"""Tag JobPipeline 执行与落库收尾。"""
from __future__ import annotations

import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from core.infra.project_context import ProjectContext
from core.infra.db.engines.duckdb.wal_policy import should_checkpoint_after_tag_run
from core.infra.job_pipeline import (
    DispatchResult,
    ExecutionBackend,
    Job,
    JobPipeline,
    JobPipelineSettings,
    JobReport,
    RunProgress,
)
from core.infra.job_pipeline.profile import (
    WorkerProfiles,
    profile_max_parallel_jobs_cap,
    profile_reserve_cores,
)
from core.infra.job_pipeline.profile.probe import WorkerProbe
from core.modules.tag.engines.shared.backend import backend_is_duckdb, parse_execute_mode
from core.modules.tag.engines.shared.report_save_buffer import TagReportSaveBuffer
from core.modules.tag.engines.shared.run_profile import TagRunProfile
from core.modules.tag.engines.shared.worker_exec import execute_tag_job
from core.modules.tag.services.discovery.path_rules import filesystem_safe_tag_key

logger = logging.getLogger(__name__)


def _make_tag_spill_dir(scenario_name: str) -> Path:
    """DuckDB stage spill 临时目录（``tag_key`` 含 ``/`` 时须 sanitize prefix）。"""
    parent = ProjectContext.path.get_userspace_tmp_directory() / "tag_spill"
    parent.mkdir(parents=True, exist_ok=True)
    prefix = f"ntq_tag_{filesystem_safe_tag_key(scenario_name)}_"
    return Path(tempfile.mkdtemp(prefix=prefix, dir=str(parent)))


def maybe_checkpoint_duckdb_after_tag_run(data_mgr: Any) -> None:
    db = getattr(data_mgr, "db", None) if data_mgr else None
    if db is None or str(db.config.get("database_type") or "").lower() != "duckdb":
        return
    if not should_checkpoint_after_tag_run(db.config):
        return
    try:
        results = db.checkpoint_duckdb()
        if not results:
            return
        failed = [d for d, ok in results.items() if not ok]
        ok_domains = sorted(d for d, ok in results.items() if ok)
        if failed:
            logger.warning(
                "DuckDB WAL 合并未完成: 失败 domain=%s；成功=%s。"
                "（写队列忙时可重试 devcli.py dbc --recover）",
                failed,
                ok_domains,
            )
        else:
            logger.info("DuckDB WAL 已合并（domains=%s）", ok_domains)
    except Exception as exc:
        logger.warning(
            "Tag 完成后 CHECKPOINT 异常（若下次启动报 WAL: python devcli.py dbc --recover）: %s",
            exc,
        )


def execute_tag_jobs(
    *,
    data_mgr: Any,
    tag_data_service: Any,
    jobs: List[Dict[str, Any]],
    scenario_name: str,
    performance: Optional[Dict[str, Any]] = None,
    profile_enabled: bool = False,
    on_tag_data_service_refresh: Optional[Callable[[Any], None]] = None,
    on_pipeline_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    """运行 dispatch jobs 并攒批 save_batch。"""
    performance = performance or {}
    stage_in_worker = performance.get("stage_in_worker", True)
    if isinstance(stage_in_worker, str):
        stage_in_worker = stage_in_worker.strip().lower() in ("1", "true", "yes")
    else:
        stage_in_worker = bool(stage_in_worker)
    if os.environ.get("NTQ_TAG_STAGE_IN_WORKER", "").strip().lower() in (
        "1",
        "true",
        "yes",
    ):
        stage_in_worker = True

    duckdb_stage_spill = stage_in_worker and backend_is_duckdb(data_mgr)
    save_batch_size = int(performance.get("save_batch_size", 5000))
    dispatch_settings = JobPipelineSettings(
        worker=ExecutionBackend.PROCESS,
        execute_mode=parse_execute_mode(performance.get("execute_mode")),
        max_workers=performance.get("max_workers", "auto"),
        batch_size=int(performance.get("batch_size", 10)),
        prefetch_ahead=int(performance.get("prefetch_ahead", 1)),
        worker_profile=WorkerProfiles.TAG,
        duckdb_process_pool_scope="auto",
        duckdb_data_mgr=data_mgr,
        duckdb_resume_main_after_pool=not duckdb_stage_spill,
    )
    run_name = f"tag:{scenario_name}"
    total_jobs = len(jobs)
    entity_count = sum(
        len(j["payload"].get("entities") or [{"entity_id": j["payload"].get("entity_id")}])
        for j in jobs
        if j.get("payload")
    )
    start_time = time.time()
    profile = TagRunProfile(enabled=profile_enabled)
    for job in jobs:
        if job.get("payload") and stage_in_worker:
            job["payload"]["_stage_in_worker"] = True

    real_save_fn = tag_data_service.save_batch

    # Dry run 模式：使用 mock 函数跳过数据库写入
    dry_run = performance.get("dry_run", False)
    if dry_run:
        def _dry_save_fn(rows: List[Any]) -> int:
            """Dry run: 记录但不实际写入"""
            logger.debug("[DRY RUN] 跳过写入 %d 行 tag 数据", len(rows))
            return len(rows)
        real_save_fn = _dry_save_fn
        logger.info("[DRY RUN] 已启用 dry run 模式，所有 save_batch 操作将被跳过")

    spill_dir: Optional[Path] = None
    if duckdb_stage_spill:
        spill_rows = int(performance.get("stage_spill_rows") or 50_000)
        spill_dir = _make_tag_spill_dir(scenario_name)
        save_buffer = TagReportSaveBuffer(
            real_save_fn,
            batch_size=save_batch_size,
            accumulate_only=True,
            spill_row_threshold=spill_rows,
            spill_dir=spill_dir,
        )
    else:
        save_buffer = TagReportSaveBuffer(real_save_fn, batch_size=save_batch_size)

    progress_state = {"last_pct": -1, "finished": 0}

    def on_result(report: JobReport, progress: RunProgress) -> None:
        t0 = time.perf_counter()
        save_batch_sec = 0.0
        if not report.success:
            logger.error(
                "Tag job 失败: job_id=%s error=%s",
                report.job_id,
                report.error,
            )
        else:
            data = report.data if isinstance(report.data, dict) else {}
            stage_sec = data.get("_profile_stage_sec")
            if isinstance(stage_sec, (int, float)):
                profile.record_stage(
                    elapsed_sec=float(stage_sec),
                    payload=data.get("_stage_payload_hint") or {},
                )
            exec_sec = data.get("_profile_execute_sec")
            if isinstance(exec_sec, (int, float)):
                profile.record_execute(float(exec_sec))
            tag_values = data.get("tag_values") or []
            if tag_values:
                save_batch_sec = save_buffer.extend_in_chunks(tag_values)

        profile.record_report(
            elapsed_sec=time.perf_counter() - t0,
            save_batch_sec=save_batch_sec,
        )

        progress_state["finished"] = progress.finished
        finished = progress_state["finished"]
        pct = int(finished * 100 / total_jobs) if total_jobs else 100
        if finished == total_jobs or pct >= progress_state["last_pct"] + 1:
            logger.info(
                "[%s] Tag 进度: %s/%s (%s%%) 成功=%s 失败=%s",
                run_name,
                finished,
                total_jobs,
                pct,
                progress.ok,
                progress.fail,
            )
            progress_state["last_pct"] = pct
            if on_pipeline_progress is not None:
                try:
                    on_pipeline_progress(
                        {
                            "finished": finished,
                            "total_jobs": total_jobs,
                            "progress_pct": float(pct),
                            "ok": progress.ok,
                            "fail": progress.fail,
                        }
                    )
                except Exception as exc:
                    logger.warning("on_pipeline_progress failed: %s", exc)

    dispatcher_jobs = [Job(job_id=job["id"], payload=job["payload"]) for job in jobs]
    resolved_workers = WorkerProbe.resolve(
        dispatch_settings.max_workers,
        reserve_cores=profile_reserve_cores(WorkerProfiles.TAG),
        cap=profile_max_parallel_jobs_cap(WorkerProfiles.TAG),
    )
    logger.info(
        "[%s] 🚀 开始执行 dispatch_jobs=%s entities=%s (workers=%s, max_workers=%r, "
        "reserve_cores=%s, mode=%s, stage_in_worker=%s)",
        run_name,
        total_jobs,
        entity_count,
        resolved_workers,
        dispatch_settings.max_workers,
        dispatch_settings.reserve_cores,
        dispatch_settings.execute_mode.value,
        stage_in_worker,
    )

    dispatch_result = DispatchResult(total=total_jobs, run_name=run_name)
    interrupted = False
    spill_rows = int(performance.get("stage_spill_rows") or 50_000)
    try:
        if stage_in_worker and duckdb_stage_spill:
            logger.info(
                "[%s] stage_in_worker + DuckDB spill（buffer≥%d 行 Parquet，池结束后写 tag）",
                run_name,
                spill_rows,
            )
        elif stage_in_worker:
            from core.modules.tag.engines.shared.backend import configured_database_type

            logger.info(
                "[%s] stage_in_worker（%s：on_result 攒批直接 save_batch）",
                run_name,
                configured_database_type(data_mgr),
            )
        dispatcher = JobPipeline(
            settings=dispatch_settings,
            execute=execute_tag_job,
            on_result=on_result,
        )
        dispatch_result = dispatcher.run(dispatcher_jobs, run_name=run_name)
        if dispatch_result.failed and dispatch_result.failures:
            for item in dispatch_result.failures[:5]:
                logger.error(
                    "Dispatch failure: job_id=%s phase=%s error=%s",
                    item.job_id,
                    getattr(item.phase, "value", item.phase),
                    item.error,
                )
    except KeyboardInterrupt:
        interrupted = True
        logger.warning(
            "[%s] 用户中断 (Ctrl+C)：等待 worker 退出后 flush 已攒批数据…",
            run_name,
        )
        raise
    finally:
        if duckdb_stage_spill:
            logger.info("[%s] ⏳ 等待 tag 数据写入完成…", run_name)
            from core.infra.db.engines.duckdb.process_pool_scope import (
                resume_main_database_with_retry,
            )
            from core.modules.tag.engines.shared.staging.worker_runtime import (
                digest_stage_in_worker_save_buffer,
            )

            try:
                save_sec = digest_stage_in_worker_save_buffer(
                    data_mgr,
                    save_buffer,
                    batch_size=save_batch_size,
                )
                if save_sec > 0:
                    logger.info(
                        "[%s] DuckDB 收尾写库 %.2fs（%s 行，spills=%s）",
                        run_name,
                        save_sec,
                        save_buffer.saved_row_count,
                        save_buffer.spill_count,
                    )
                resume_main_database_with_retry(data_mgr)
                if on_tag_data_service_refresh:
                    on_tag_data_service_refresh(data_mgr.stock.tags)
            except Exception as exc:
                logger.warning("[%s] stage 收尾失败: %s", run_name, exc)
            save_buffer.cleanup_spill_dir()
        else:
            logger.info("[%s] ⏳ 等待 tag 数据写入完成…", run_name)
            try:
                save_buffer.flush()
            except Exception as exc:
                logger.warning("[%s] 收尾 flush 失败: %s", run_name, exc)

        db = getattr(data_mgr, "db", None) if data_mgr else None
        if db is not None:
            try:
                db.wait_for_writes(timeout=60.0 if not interrupted else 15.0)
                logger.info("[%s] ✅ tag 数据写入完成", run_name)
                maybe_checkpoint_duckdb_after_tag_run(data_mgr)
            except Exception as exc:
                logger.warning("[%s] 等待写入或 CHECKPOINT 失败: %s", run_name, exc)

    elapsed_time = time.time() - start_time
    saved_tag_count = save_buffer.saved_row_count
    logger.info(
        "Tag计算完成: scenario=%s, dispatch_jobs=%s, entities=%s, "
        "成功=%s, 失败=%s, 写入tag_values=%s, save_batch次数=%s, 耗时=%.2fs",
        scenario_name,
        total_jobs,
        entity_count,
        dispatch_result.completed,
        dispatch_result.failed,
        saved_tag_count,
        save_buffer.flush_count,
        elapsed_time,
    )
    from core.modules.tag.engines.shared.backend import configured_database_type

    for line in profile.summary_lines(
        total_jobs=total_jobs,
        database_type=configured_database_type(data_mgr),
    ):
        logger.info(line)

    # 构建性能报告数据
    wall_time = time.time() - start_time
    profile_data = None
    if profile.enabled:
        profile_data = {
            "stage_sec": round(profile.stage_sec, 3),
            "execute_sec": round(profile.execute_sec, 3),
            "report_sec": round(profile.report_sec, 3),
            "save_batch_sec": round(profile.save_batch_sec, 3),
            "stage_jobs": profile.stage_jobs,
            "execute_jobs": profile.execute_jobs,
            "report_jobs": profile.report_jobs,
            "pickle_bytes": profile.pickle_bytes,
            "payload_rows": profile.payload_rows,
            "wall_sec": round(wall_time, 3),
        }

    return {
        "scenario_name": scenario_name,
        "total_jobs": total_jobs,
        "completed_jobs": dispatch_result.completed,
        "failed_jobs": dispatch_result.failed,
        "saved_tag_values": saved_tag_count,
        "elapsed_time": elapsed_time,
        "dispatch_result": dispatch_result,
        "profile": profile_data,
        "entity_count": entity_count,
    }
