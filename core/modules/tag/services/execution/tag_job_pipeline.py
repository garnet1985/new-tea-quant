"""Tag Timeline / Sliced：BacktestEngine 执行入口。

职责边界：
- Tag 负责：构建 jobs、execute_fn（子进程/编排逻辑）、主进程阶段性 save、进度上报
- BacktestEngine 负责：探针、规划、切割、执行、监控

Tag 入库逻辑：
- timeline：子进程返回 tag_values → 主进程 on_result 攒批 save
- sliced：orchestrator 每 slice 回调 → 主进程 TagReportSaveBuffer 阶段性 save_batch
- engine.run() 返回后 flush 剩余缓冲
"""
from __future__ import annotations

import contextvars
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from core.modules.backtest_engine.contracts import BacktestJob, JobContext, JobReport, RunCallbacks, RunProgress
from core.modules.backtest_engine.core.shared.default_performance import merge_performance
from core.modules.tag.settings.worker_profile import (
    profile_tag_calendar_slice_config,
    profile_tag_entity_timeline_config,
)

logger = logging.getLogger(__name__)

TAG_TIMELINE_EXECUTOR_KEY = "tag"
TAG_SLICED_EXECUTOR_KEY = "tag"

_slice_save_hook: contextvars.ContextVar[
    Optional[Callable[[List[Dict[str, Any]]], None]]
] = contextvars.ContextVar("tag_slice_save_hook", default=None)

__all__ = [
    "TAG_SLICED_EXECUTOR_KEY",
    "TAG_TIMELINE_EXECUTOR_KEY",
    "execute_tag_sliced_job",
    "execute_tag_timeline_job",
    "run_tag_sliced_via_backtest_engine",
    "run_tag_timeline_via_backtest_engine",
]


# ============================================================
# 子进程入口
# ============================================================

def _merge_timeline_wire_jobs(
    wire_jobs: List[Dict[str, Any]],
    batch_job_id: str,
) -> Dict[str, Any]:
    """BacktestEngine timeline batch / probe：``{'jobs': [BacktestJob wire...]}`` → worker payload。"""
    rows = BacktestJob.batch_payloads(wire_jobs)
    if len(rows) == 1:
        merged = dict(rows[0])
        merged.setdefault("_job_id", batch_job_id)
        return merged

    base = dict(rows[0])
    entities = [
        {
            key: row[key]
            for key in ("entity_id", "start_date", "end_date")
            if key in row
        }
        for row in rows
    ]
    merged = {
        key: value
        for key, value in base.items()
        if key not in {"entity_id", "start_date", "end_date", "_job_id"}
    }
    merged["entities"] = entities
    merged["_job_id"] = batch_job_id
    return merged


def _resolve_timeline_worker_payload(context: JobContext) -> Dict[str, Any]:
    payload = dict(context.payload)
    wire_jobs = payload.get("jobs")
    if isinstance(wire_jobs, list) and wire_jobs:
        merged = _merge_timeline_wire_jobs(wire_jobs, context.job_id)
        for key, value in payload.items():
            if str(key).startswith("_") and key not in merged:
                merged[key] = value
        return merged
    return payload


def execute_tag_timeline_job(context: JobContext) -> Dict[str, Any]:
    """BacktestEngine timeline 子进程入口。

    流程：
    1. 提取 payload
    2. 可选 stage_in_worker（DuckDB spill 模式）
    3. 单 entity 或 batch 执行
    4. 返回 tag_values（不入库，由主进程 on_result 积攒写入）

    Args:
        context: BacktestEngine 提供的 job 上下文

    Returns:
        Dict[str, Any]: 包含 success/tag_values/errors/profile 的结果
    """
    from core.modules.tag.engines.shared.worker_exec import (
        maybe_stage_in_worker,
        run_worker_for_payload,
        execute_batch_entities,
    )
    from core.modules.tag.engines.shared.staging.worker_runtime import (
        payload_needs_worker_stage,
        release_worker_runtime,
    )

    payload = _resolve_timeline_worker_payload(context)

    # 可选 stage_in_worker（DuckDB spill 模式下在子进程内准备数据）
    staged_payload, stage_sec = maybe_stage_in_worker(payload)

    try:
        # 单 entity 或 batch 执行
        entities = staged_payload.get("entities")
        if isinstance(entities, list) and len(entities) > 1:
            result = execute_batch_entities(staged_payload, entities)
        else:
            result = run_worker_for_payload(staged_payload)

        # 附加 profile 数据
        if stage_sec > 0:
            result["_profile_stage_sec"] = stage_sec

        return result

    finally:
        # 释放 worker runtime（stage_in_worker 模式下需要）
        if payload_needs_worker_stage(payload):
            release_worker_runtime()


# ============================================================
# Job 包装
# ============================================================

def _wrap_tag_timeline_job(
    index: int,
    job_dict: Dict[str, Any],
    *,
    stage_in_worker: bool = False,
) -> Dict[str, Any]:
    """将 tag 的 job_dict 包装为 BacktestJob wire format。

    Args:
        index: job 序号
        job_dict: build_timeline_jobs 返回的 ``{'id', 'payload'}`` 字典

    Returns:
        Dict: BacktestJob wire format ``{'id': str, 'payload': dict}``
    """
    if isinstance(job_dict.get("payload"), dict):
        job = BacktestJob.from_dict(job_dict)
        payload = dict(job.payload)
        payload.setdefault("_job_id", job.id)
        payload["_executor"] = TAG_TIMELINE_EXECUTOR_KEY
        if stage_in_worker:
            payload["_stage_in_worker"] = True
        return BacktestJob(id=job.id, payload=payload).to_dict()

    job_id = str(job_dict.get("job_id") or job_dict.get("id") or f"tag_timeline_{index}")
    payload = dict(job_dict)
    payload.pop("id", None)
    payload.pop("job_id", None)
    payload.setdefault("_job_id", job_id)
    payload["_executor"] = TAG_TIMELINE_EXECUTOR_KEY
    if stage_in_worker:
        payload["_stage_in_worker"] = True
    return BacktestJob(id=job_id, payload=payload).to_dict()


# ============================================================
# 主进程入口
# ============================================================

def run_tag_timeline_via_backtest_engine(
    *,
    timeline_jobs: List[Dict[str, Any]],
    settings: Dict[str, Any],
    run_name: str = "tag",
    total_entities: int = 0,
    on_pipeline_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
    duckdb_data_mgr: Any = None,
) -> Dict[str, Any]:
    """Tag timeline 模式：组装 jobs + execute_fn，交给 BacktestEngine。

    流程：
    1. 包装 timeline_jobs 为 BacktestJob 格式
    2. 创建 TagReportSaveBuffer（积攒入库）
    3. 创建 on_result 回调（积攒 tag_values + 上报进度）
    4. 调用 BacktestEngine.timeline.run()
    5. flush save_buffer（批量入库）
    6. DuckDB CHECKPOINT

    Args:
        timeline_jobs: build_timeline_jobs 返回的 job 列表
        settings: 配置字典（包含 performance 等）
        run_name: 运行名称
        total_entities: 总 entity 数量
        on_pipeline_progress: 进度回调
        duckdb_data_mgr: DuckDB 数据管理器

    Returns:
        Dict[str, Any]: 执行统计
    """
    from core.modules.backtest_engine import BacktestEngine
    from core.modules.tag.engines.shared.report_save_buffer import TagReportSaveBuffer
    from core.modules.tag.engines.shared.runner import (
        _make_tag_spill_dir,
        maybe_checkpoint_duckdb_after_tag_run,
    )
    from core.modules.tag.engines.shared.backend import backend_is_duckdb
    from core.modules.tag.engines.shared.staging.worker_runtime import (
        digest_stage_in_worker_save_buffer,
    )
    from core.infra.db.engines.duckdb.process_pool_scope import (
        resume_main_database_with_retry,
    )

    performance = settings.get("performance") or {}
    stage_in_worker = _resolve_stage_in_worker(performance)
    scenario_name = settings.get("scenario_name", "")
    dry_run = bool(performance.get("dry_run", False))
    save_batch_size = int(performance.get("save_batch_size", 500))

    # ---- 1. 包装 timeline_jobs 为 BacktestJob 格式 ----
    engine_jobs = [
        _wrap_tag_timeline_job(i, job, stage_in_worker=stage_in_worker)
        for i, job in enumerate(timeline_jobs)
    ]

    # ---- 2. 创建 TagReportSaveBuffer ----
    is_duckdb = duckdb_data_mgr is not None and backend_is_duckdb(duckdb_data_mgr)
    spill_dir = None
    save_buffer: Optional[TagReportSaveBuffer] = None

    if stage_in_worker and is_duckdb:
        # DuckDB spill 模式：进程池期间攒 Parquet，池结束后统一写库
        spill_dir = _make_tag_spill_dir(scenario_name)
        save_buffer = TagReportSaveBuffer(
            save_fn=_dry_run_save_fn if dry_run else _make_tag_save_fn(scenario_name),
            batch_size=save_batch_size,
            accumulate_only=True,
            spill_row_threshold=int(performance.get("spill_row_threshold", 5000)),
            spill_dir=spill_dir,
        )
    else:
        # 非 spill 模式：直接攒批入库
        save_buffer = TagReportSaveBuffer(
            save_fn=_dry_run_save_fn if dry_run else _make_tag_save_fn(scenario_name),
            batch_size=save_batch_size,
        )

    # ---- 3. 创建 on_result 回调 ----
    total_jobs = len(engine_jobs)
    finished_count = 0
    ok_count = 0
    fail_count = 0
    saved_tag_values = 0
    profile_data: List[Dict[str, Any]] = []
    start_time = time.monotonic()

    def on_engine_result(report: JobReport, progress: RunProgress) -> None:
        nonlocal finished_count, ok_count, fail_count, saved_tag_values

        finished_count += 1
        data = report.data if isinstance(report.data, dict) else {}

        if report.success:
            ok_count += 1
        else:
            fail_count += 1

        # 积攒 tag_values 到 save_buffer
        tag_values = data.get("tag_values") or []
        if tag_values:
            save_buffer.extend_in_chunks(tag_values)
            saved_tag_values += len(tag_values)

        # 记录 profile
        profile_entry = {
            "job_id": report.job_id,
            "success": report.success,
        }
        if data.get("_profile_execute_sec"):
            profile_entry["execute_sec"] = data["_profile_execute_sec"]
        if data.get("_profile_stage_sec"):
            profile_entry["stage_sec"] = data["_profile_stage_sec"]
        profile_data.append(profile_entry)

        # 上报进度
        if on_pipeline_progress is not None:
            total = max(total_entities, total_jobs)
            progress_pct = min(100.0, finished_count / total * 100.0) if total > 0 else 0.0
            on_pipeline_progress({
                "finished": finished_count,
                "total": total,
                "ok": ok_count,
                "fail": fail_count,
                "progress_pct": progress_pct,
            })

    # ---- 4. 调用 BacktestEngine.entity_based.run() ----
    dispatch_performance = merge_performance(
        profile_tag_entity_timeline_config(),
        performance,
    )
    result = BacktestEngine.entity_based.run(
        engine_jobs,
        execute_tag_timeline_job,
        performance=dispatch_performance,
        task_name=run_name,
        callbacks=RunCallbacks(on_result=on_engine_result),
    )

    # ---- 5. flush save_buffer（批量入库）----
    try:
        if stage_in_worker and is_duckdb:
            # DuckDB spill 模式：读取 spill 文件 + 内存缓冲，统一写库
            digest_stage_in_worker_save_buffer(
                save_buffer,
                scenario_name=scenario_name,
            )
            # 恢复主进程数据库连接
            resume_main_database_with_retry()
        else:
            # 非 spill 模式：直接 flush
            save_buffer.flush()
    except Exception as exc:
        logger.error("Tag save_buffer flush 失败: %s", exc, exc_info=True)

    # ---- 6. DuckDB CHECKPOINT ----
    if is_duckdb and duckdb_data_mgr is not None:
        try:
            maybe_checkpoint_duckdb_after_tag_run(duckdb_data_mgr)
        except Exception as exc:
            logger.warning("DuckDB CHECKPOINT 失败: %s", exc)

    # 清理 spill 目录
    if spill_dir is not None:
        try:
            save_buffer.cleanup_spill_dir()
        except Exception:
            pass

    elapsed_seconds = time.monotonic() - start_time

    return {
        "scenario_name": scenario_name,
        "total_jobs": total_jobs,
        "completed_jobs": ok_count,
        "failed_jobs": fail_count,
        "saved_tag_values": saved_tag_values,
        "elapsed_time": elapsed_seconds,
        "entity_count": total_entities,
        "dispatch_result": result,
        "profile": profile_data,
    }


# ============================================================
# Sliced 子进程/编排入口（BacktestEngine.sliced 在主进程内调用）
# ============================================================

SLICED_ENGINE_METADATA_KEYS = frozenset(
    {
        "_job_id",
        "_slice_plan",
        "_slice_probe",
        "_probe_max_slices",
        "_probe_slice_open_days",
        "_probe_job_id",
        "_task_name",
        "_executor",
    }
)


def execute_tag_sliced_job(context: JobContext) -> Dict[str, Any]:
    """BacktestEngine sliced 入口：calendar_slice orchestrator + 主进程 slice save 钩子。"""
    from core.modules.tag.engines.sliced.worker import run_tag_calendar_slice_payload

    payload = {
        key: value
        for key, value in dict(context.payload).items()
        if key in SLICED_ENGINE_METADATA_KEYS or not str(key).startswith("_")
    }
    exec_t0 = time.monotonic()
    hook = _slice_save_hook.get()
    try:
        out = run_tag_calendar_slice_payload(
            payload,
            on_slice_tag_values=hook,
        )
        out["_profile_execute_sec"] = time.monotonic() - exec_t0
        return out
    except Exception as exc:
        logger.exception("Tag calendar_slice job failed: %s", exc)
        return {
            "success": False,
            "bulk": True,
            "tag_values": [],
            "entity_count": len(payload.get("entity_ids") or []),
            "error": str(exc),
            "_profile_execute_sec": time.monotonic() - exec_t0,
        }


def _wrap_tag_sliced_dispatch_job(job: Dict[str, Any]) -> Dict[str, Any]:
    job_id = str(job.get("job_id") or job.get("id") or "tag_calendar_slice")
    payload = {
        key: value
        for key, value in job.items()
        if key not in ("job_id", "id")
    }
    payload.setdefault("_job_id", job_id)
    payload["_executor"] = TAG_SLICED_EXECUTOR_KEY
    return BacktestJob(id=job_id, payload=payload).to_dict()


def run_tag_sliced_via_backtest_engine(
    *,
    dispatch_jobs: List[Dict[str, Any]],
    settings: Dict[str, Any],
    run_name: str = "tag",
    on_pipeline_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
    duckdb_data_mgr: Any = None,
    on_tag_data_service_refresh: Optional[Callable[[Any], None]] = None,
) -> Dict[str, Any]:
    """Tag calendar_slice：单 bulk job → BacktestEngine.sliced + 主进程阶段性 save。"""
    from core.modules.backtest_engine import BacktestEngine
    from core.modules.tag.engines.shared.report_save_buffer import TagReportSaveBuffer
    from core.modules.tag.engines.shared.runner import maybe_checkpoint_duckdb_after_tag_run
    from core.modules.tag.engines.shared.backend import backend_is_duckdb

    performance = settings.get("performance") or {}
    scenario_name = settings.get("scenario_name", "")
    dry_run = bool(performance.get("dry_run", False))
    save_batch_size = int(performance.get("save_batch_size", 5000))

    engine_jobs = [_wrap_tag_sliced_dispatch_job(job) for job in dispatch_jobs]
    save_buffer = TagReportSaveBuffer(
        save_fn=_dry_run_save_fn if dry_run else _make_tag_save_fn(scenario_name),
        batch_size=save_batch_size,
    )

    saved_tag_values = 0
    start_time = time.monotonic()

    def on_slice_tag_values(rows: List[Dict[str, Any]]) -> None:
        nonlocal saved_tag_values
        if not rows:
            return
        save_buffer.extend_in_chunks(rows)
        saved_tag_values += len(rows)

    finished_count = 0
    ok_count = 0
    fail_count = 0

    def on_engine_result(report: JobReport, progress: RunProgress) -> None:
        nonlocal finished_count, ok_count, fail_count
        finished_count += 1
        if report.success:
            ok_count += 1
        else:
            fail_count += 1
        if on_pipeline_progress is not None:
            on_pipeline_progress(
                {
                    "finished": finished_count,
                    "total": max(len(engine_jobs), 1),
                    "ok": ok_count,
                    "fail": fail_count,
                    "progress_pct": min(
                        100.0,
                        finished_count / max(len(engine_jobs), 1) * 100.0,
                    ),
                }
            )

    hook_token = _slice_save_hook.set(on_slice_tag_values)
    try:
        result = BacktestEngine.slice_based.run(
            engine_jobs,
            execute_tag_sliced_job,
            performance=merge_performance(
                profile_tag_calendar_slice_config(),
                performance,
            ),
            task_name=run_name,
            callbacks=RunCallbacks(on_result=on_engine_result),
        )
    finally:
        _slice_save_hook.reset(hook_token)

    try:
        save_buffer.flush()
    except Exception as exc:
        logger.error("Tag sliced save_buffer flush 失败: %s", exc, exc_info=True)

    db = getattr(duckdb_data_mgr, "db", None) if duckdb_data_mgr else None
    if db is not None:
        try:
            db.wait_for_writes(timeout=60.0)
            if on_tag_data_service_refresh is not None:
                on_tag_data_service_refresh(duckdb_data_mgr.stock.tags)
        except Exception as exc:
            logger.warning("[%s] 等待 tag 写入失败: %s", run_name, exc)

    if duckdb_data_mgr is not None and backend_is_duckdb(duckdb_data_mgr):
        try:
            maybe_checkpoint_duckdb_after_tag_run(duckdb_data_mgr)
        except Exception as exc:
            logger.warning("DuckDB CHECKPOINT 失败: %s", exc)

    elapsed_seconds = time.monotonic() - start_time
    saved_row_count = save_buffer.saved_row_count

    return {
        "scenario_name": scenario_name,
        "total_jobs": len(engine_jobs),
        "completed_jobs": ok_count,
        "failed_jobs": fail_count,
        "saved_tag_values": saved_row_count or saved_tag_values,
        "elapsed_time": elapsed_seconds,
        "dispatch_result": result,
        "profile": None,
        "entity_count": sum(len(j.get("entity_ids") or []) for j in dispatch_jobs),
    }


# ============================================================
# 辅助函数
# ============================================================

def _resolve_stage_in_worker(performance: Dict[str, Any]) -> bool:
    """解析 stage_in_worker 配置。"""
    import os

    if os.environ.get("NTQ_TAG_STAGE_IN_WORKER") is not None:
        return os.environ.get("NTQ_TAG_STAGE_IN_WORKER", "").lower() in ("1", "true", "yes")

    return bool(performance.get("stage_in_worker", False))


def _dry_run_save_fn(rows: List[Any]) -> int:
    """Dry run 模式：跳过数据库写入。"""
    return len(rows)


def _make_tag_save_fn(scenario_name: str) -> Callable[[List[Any]], int]:
    """创建 tag_values 写库函数（使用 tag_data_service.save_batch）。"""
    def save_fn(rows: List[Any]) -> int:
        from core.modules.data_manager import DataManager

        data_mgr = DataManager.get_instance()
        if data_mgr is None:
            data_mgr = DataManager(is_verbose=False)
        data_mgr.stock.tags.save_batch(rows)
        return len(rows)
    return save_fn
