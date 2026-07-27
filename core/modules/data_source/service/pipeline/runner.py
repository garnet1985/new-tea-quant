"""Data source 多 bundle 执行：私有 JobPipeline（线程队列）+ on_result 写库。"""
from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, List, Tuple, Union

from core.modules.data_source.data_class.api_job import ApiJob
from core.modules.data_source.data_class.api_job_bundle import ApiJobBundle
from core.modules.data_source.data_class.config import DataSourceConfig
from core.modules.data_source.service.api_job_executor import ApiJobExecutor
from core.modules.data_source.service.executor.bundle_progress import (
    clear as clear_bundle_progress,
    install as install_bundle_progress,
)
from core.modules.data_source.service.pipeline.async_bridge import run_async_in_sync
from core.modules.data_source.service.pipeline.job_pipeline import (
    Job,
    JobContext,
    JobPipeline,
    JobPipelineSettings,
    JobReport,
    RunProgress,
)
from core.modules.data_source.service.pipeline.save_buffer import DataSourceSaveBuffer
from core.modules.data_source.service.pipeline.save_utils import (
    BundleSaveItem,
    checkpoint_after_batch_save,
    has_actual_data,
)

logger = logging.getLogger(__name__)

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
        on_after_single_bundle_complete: Callable[
            [Dict[str, Any], Any, Dict[str, Any]], Any
        ],
        on_after_batch_bundles_complete: Callable[
            [Dict[str, Any], List[BundleSaveItem]], Any
        ],
        enrich_result_for_batch: Callable[
            [Dict[str, Any], ApiJobBundle, Dict[str, Any]], Dict[str, Any]
        ],
    ) -> Dict[str, Any]:
        bundles = normalize_job_bundles(context, jobs)
        if not bundles:
            return {}

        config: DataSourceConfig = context.get("config")
        if not config:
            raise ValueError("config 必须配置 save_mode")

        data_source_key = str(context.get("data_source_key") or "data_source")
        save_mode = config.get_save_mode()
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
        save_buffer = DataSourceSaveBuffer(
            context=context,
            config=config,
            save_mode=save_mode,
            total_bundles=total_bundles,
            on_single_bundle_complete=on_after_single_bundle_complete,
            on_batch_bundles_complete=on_after_batch_bundles_complete,
            bundle_progress=bundle_progress,
        )

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
            logger.info(bundle_progress.format_short())
            progress_state["last_done"] = finished
            progress_state["last_log_at"] = now
            progress_state["last_pct"] = pct

        def on_result(report: JobReport, progress: RunProgress) -> None:
            if not report.success:
                logger.warning(
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
                merged.update(result)
                if save_buffer.saves_enabled and job_bundle is not None:
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
            max_workers="auto",
            prefetch_ahead=2,
            continue_on_failure=True,
        )
        run_name = f"ds:{data_source_key}"

        logger.info("[%s] 开始抓取（线程队列），共 %s 个 bundle", data_source_key, total_bundles)

        dispatcher = JobPipeline(
            settings=settings,
            execute=execute,
            on_result=on_result,
        )

        try:
            dispatch_result = dispatcher.run(pipeline_jobs, run_name=run_name)
        except KeyboardInterrupt:
            logger.warning("[%s] 抓取中断", data_source_key)
            raise
        finally:
            try:
                save_buffer.flush_remaining()
            except Exception:
                pass
            checkpoint_after_batch_save(context)
            snap = bundle_progress.snapshot()
            if snap["failed"]:
                logger.warning(
                    "[%s] 抓取结束 %s/%s（%s%%），失败 %s",
                    data_source_key,
                    snap["done"],
                    snap["total"],
                    snap["pct"],
                    snap["failed"],
                )
            else:
                logger.info(
                    "[%s] 抓取结束 %s/%s（%s%%）",
                    data_source_key,
                    snap["done"],
                    snap["total"],
                    snap["pct"],
                )
            clear_bundle_progress()

        if dispatch_result.failed:
            logger.warning(
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
