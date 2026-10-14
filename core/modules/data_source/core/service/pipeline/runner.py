"""Data source 多 bundle 执行：私有 JobPipeline（线程队列）+ on_result 写库。"""
from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, List, Tuple, Union

from core.modules.data_source.core.data_class.api_job import ApiJob
from core.modules.data_source.core.data_class.api_job_bundle import ApiJobBundle
from core.modules.data_source.core.service.api_job_executor import ApiJobExecutor
from core.modules.data_source.core.service.executor.bundle_progress import (
    clear as clear_bundle_progress,
    install as install_bundle_progress,
)
from core.modules.data_source.core.service.pipeline.async_bridge import run_async_in_sync
from core.modules.data_source.core.service.pipeline.job_pipeline import (
    Job,
    JobContext,
    JobPipeline,
    JobPipelineSettings,
    JobReport,
    RunProgress,
)
from core.modules.data_source.core.service.pipeline.save_buffer import DataSourceSaveBuffer
from core.modules.data_source.core.service.pipeline.save_memory_budget import SaveMemoryBudget
from core.modules.data_source.core.service.pipeline.save_utils import (
    checkpoint_after_batch_save,
    has_actual_data,
)

logger = logging.getLogger(__name__)


def _note_bundle_error(context: Dict[str, Any], job_id: str, error: Any) -> None:
    text = str(error or "").splitlines()[0][:300]
    context["_bundle_error_count"] = int(context.get("_bundle_error_count") or 0) + 1
    lines = context.setdefault("_bundle_errors", [])
    if isinstance(lines, list) and len(lines) < 200:
        lines.append(f"{job_id}: {text}")

BundleRow = Tuple[str, List[ApiJob], Any]

PROGRESS_LOG_INTERVAL_SEC = 45
PROGRESS_LOG_EVERY_N = 100


class DataSourcePipelineRunner:
    """多 bundle 抓取：线程队列并行，保存集中在主线程 on_result。"""

    def run_bundles(
        self,
        context: Dict[str, Any],
        jobs: List[Union[ApiJobBundle, ApiJob]],
        *,
        enrich_result_for_batch: Callable[
            [Dict[str, Any], ApiJobBundle, Dict[str, Any]], Dict[str, Any]
        ],
    ) -> Dict[str, Any]:
        bundles = normalize_job_bundles(context, jobs)
        if not bundles:
            return {}

        data_source_key = str(context.get("data_source_key") or "data_source")
        providers = context.get("providers") or {}
        api_executor = ApiJobExecutor(providers=providers)

        async def run_one_bundle(api_jobs: List[ApiJob]) -> Dict[str, Any]:
            if not api_jobs:
                return {}
            return await api_executor.execute(api_jobs)

        bundle_id_to_item: Dict[str, Any] = {
            bundle_id: item for bundle_id, _apis, item in bundles
        }
        total_bundles = len(bundles)
        bundle_progress = install_bundle_progress(data_source_key, total_bundles)
        budget = context.get("_save_budget")
        if not isinstance(budget, SaveMemoryBudget):
            budget = SaveMemoryBudget()
        to_frames = context.get("_bundle_to_frames")
        save_frames = context.get("_save_frames")
        if not callable(to_frames) or not callable(save_frames):
            raise ValueError("context 缺少 _bundle_to_frames / _save_frames")
        save_buffer = DataSourceSaveBuffer(
            context=context,
            budget=budget,
            to_frames=to_frames,
            save_frames=save_frames,
            bundle_progress=bundle_progress,
        )
        context["buffer_persisted"] = True

        progress_state = {"last_pct": -1, "last_log_at": time.time(), "last_done": 0}
        merged: Dict[str, Any] = {}

        def _log_progress(progress: RunProgress, *, force: bool = False) -> None:
            finished = progress.finished
            total = progress.total or total_bundles
            pct = int(finished * 100 / total) if total else 100
            now = time.time()
            should = force or (
                finished >= progress_state["last_done"] + PROGRESS_LOG_EVERY_N
                or (
                    now - progress_state["last_log_at"] >= PROGRESS_LOG_INTERVAL_SEC
                    and finished > progress_state["last_done"]
                )
                or (finished >= total and finished > progress_state["last_done"])
            )
            if not should:
                return
            bundle_progress.completed = progress.ok
            bundle_progress.failed = progress.fail
            line = bundle_progress.format_short()
            print(line, flush=True)
            logger.info("%s", line)
            progress_state["last_done"] = finished
            progress_state["last_log_at"] = now
            progress_state["last_pct"] = pct

        def on_result(report: JobReport, progress: RunProgress) -> None:
            if not report.success:
                _note_bundle_error(context, report.job_id, report.error)
                print(
                    f"  Bundle 失败: {report.job_id} {report.error}",
                    flush=True,
                )
                logger.info(
                    "Bundle 失败: job_id=%s error=%s",
                    report.job_id,
                    report.error,
                )
                _log_progress(progress)
                return

            data = report.data if isinstance(report.data, dict) else {}
            result = data.get("result")
            if not isinstance(result, dict):
                _log_progress(progress)
                return

            job_bundle = bundle_id_to_item.get(report.job_id)
            if job_bundle is not None and isinstance(job_bundle, ApiJobBundle):
                enriched = enrich_result_for_batch(context, job_bundle, result)
                if enriched is not None:
                    result = enriched

            if has_actual_data(result):
                if context.get("retain_results"):
                    merged.update(result)
                if job_bundle is not None:
                    save_buffer.add(job_bundle, result)

            _log_progress(progress)

        def execute(job_context: JobContext) -> Dict[str, Any]:
            payload = job_context.payload
            apis = payload.get("apis") or []
            try:
                result = run_async_in_sync(run_one_bundle(apis))
                return {
                    "success": True,
                    "bundle_id": payload.get("bundle_id"),
                    "result": result,
                }
            except Exception as exc:
                logger.error(
                    "Bundle execute 异常: job_id=%s error=%s",
                    job_context.job_id,
                    exc,
                    exc_info=True,
                )
                return {"success": False, "error": str(exc)}

        pipeline_jobs = [
            Job(
                job_id=bundle_id,
                payload={"bundle_id": bundle_id, "apis": apis},
            )
            for bundle_id, apis, _item in bundles
        ]

        settings = JobPipelineSettings(
            max_workers=budget.cpu_cap,
            prefetch_ahead=2,
            continue_on_failure=True,
            in_flight_limit=budget.current_in_flight,
        )
        run_name = f"ds:{data_source_key}"

        print(f"[{data_source_key}] 开始抓取，共 {total_bundles} 个任务", flush=True)
        logger.info("[%s] 开始抓取（线程队列），共 %s 个 bundle", data_source_key, total_bundles)

        dispatcher = JobPipeline(
            settings=settings,
            execute=execute,
            on_result=on_result,
        )

        try:
            dispatch_result = dispatcher.run(pipeline_jobs, run_name=run_name)
        except KeyboardInterrupt:
            print(f"[{data_source_key}] 抓取中断", flush=True)
            logger.info("[%s] 抓取中断", data_source_key)
            raise
        finally:
            try:
                save_buffer.flush_remaining()
            except Exception:
                pass
            checkpoint_after_batch_save(context)
            snap = bundle_progress.snapshot()
            if snap["failed"]:
                print(
                    f"[{data_source_key}] 抓取结束 {snap['done']}/{snap['total']}"
                    f"（{snap['pct']}%），失败 {snap['failed']}",
                    flush=True,
                )
            else:
                print(
                    f"[{data_source_key}] 抓取结束 {snap['done']}/{snap['total']}（{snap['pct']}%）",
                    flush=True,
                )
            logger.info(
                "[%s] 抓取结束 %s/%s（%s%%），失败 %s",
                data_source_key,
                snap["done"],
                snap["total"],
                snap["pct"],
                snap["failed"],
            )
            clear_bundle_progress()

        if dispatch_result.failed:
            print(
                f"[{data_source_key}] 失败 {dispatch_result.failed}/{dispatch_result.total}",
                flush=True,
            )
            logger.info(
                "[%s] 线程队列: 失败 %s/%s",
                data_source_key,
                dispatch_result.failed,
                dispatch_result.total,
            )

        return merged


def normalize_job_bundles(
    context: Dict[str, Any],
    jobs: List[Union[ApiJobBundle, ApiJob]],
) -> List[BundleRow]:
    """将 handler jobs 列表归一化为 (bundle_id, apis, item)。"""
    bundles: List[BundleRow] = []
    data_source_key = context.get("data_source_key", "data_source")

    for i, item in enumerate(jobs or []):
        if isinstance(item, ApiJobBundle):
            bid = item.bundle_id or f"{data_source_key}_bundle_{i}"
            apis = item.apis or []
            bundles.append((bid, apis, item))
        elif isinstance(item, ApiJob):
            bid = getattr(item, "job_id", None) or f"{data_source_key}_job_{i}"
            bundles.append((bid, [item], item))
        else:
            logger.warning("未知 job 类型，已跳过: %s", type(item))

    return bundles
