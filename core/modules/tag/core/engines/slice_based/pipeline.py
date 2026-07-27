"""Tag slice_based 编排：JobBuilder → BE.slice_based.run → flush。

消费者: Tag facade / TagManager（迁移后）

本文件:
- TagSlicePipeline: 组装 jobs/callbacks/performance，跑 BE，攒批落库
  边界: 编排与落盘；不负责 discovery / MetadataEnsure
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

from core.modules.backtest_engine import BacktestEngine
from core.modules.backtest_engine.contracts import RunCallbacks
from core.modules.backtest_engine.core.performance.settings import (
    resolve_slice_based_performance,
)
from core.modules.tag.core.data_class.scenario import Scenario
from core.modules.tag.core.engines.shared.pipeline_hooks import (
    TagPipelineHooks,
    TagPipelineRunContext,
)
from core.modules.tag.core.engines.shared.services.tag_value_flush import (
    TagValueFlushService,
)
from core.modules.tag.core.engines.shared.tag_settings.tag_settings import TagSettings
from core.modules.tag.core.engines.slice_based.executor import TagSliceJobExecutor
from core.modules.tag.core.engines.slice_based.job_builder import TagSliceJobBuilder
from core.modules.tag.core.services.discovery.data.discovered_tag import EnabledTagInfo
from core.modules.tag.settings.worker_profile import profile_tag_slice_based_config

if TYPE_CHECKING:
    from core.modules.data_manager.data_services.stock.sub_services.tag_service import (
        TagDataService,
    )

logger = logging.getLogger(__name__)


class TagSlicePipeline:
    """slice_based Tag 计算编排。"""

    @classmethod
    def run(
        cls,
        *,
        tag_info: EnabledTagInfo,
        scenario: Scenario,
        entity_ids: List[str],
        tag_data_service: Optional["TagDataService"] = None,
        shm_info: Optional[Dict[str, Any]] = None,
        dry_run: bool = False,
        save_batch_size: int = 5000,
        on_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        settings = TagSettings.from_dict(
            dict(scenario.settings or {}),
            tag_key=scenario.name,
        )
        settings.apply_defaults()
        period = settings.resolve_period()

        jobs = TagSliceJobBuilder.build_backtest_engine_jobs(
            tag_info,
            scenario,
            entity_ids,
            shm_info or {},
        )
        if not jobs:
            return {
                "success": True,
                "jobs": 0,
                "saved_tag_values": 0,
                "tag_values_count": 0,
                "message": "no jobs",
            }

        flush = TagValueFlushService(
            tag_data_service,
            dry_run=dry_run,
            batch_size=save_batch_size,
        )
        performance = resolve_slice_based_performance(profile_tag_slice_based_config())
        run_ctx = TagPipelineRunContext(
            flush=flush,
            total_jobs=len(jobs),
            on_progress=on_progress,
        )
        TagPipelineHooks.bind(run_ctx)
        t0 = time.monotonic()
        saved = 0
        try:
            base_cb = TagSliceJobExecutor.build_run_callbacks()
            callbacks = RunCallbacks(
                on_before_task_start=base_cb.on_before_task_start,
                on_tick=base_cb.on_tick,
                on_ticks_complete=base_cb.on_ticks_complete,
                on_task_result=TagPipelineHooks.on_task_result,
            )

            logger.info(
                "TagSlicePipeline start: scenario=%s entities=%d jobs=%d dry_run=%s",
                scenario.name,
                len(entity_ids),
                len(jobs),
                dry_run,
            )
            BacktestEngine.slice_based.run(
                jobs=jobs,
                start=period.start_date,
                end=period.end_date,
                performance=performance,
                callbacks=callbacks,
                task_name=f"tag:{scenario.name}",
            )
            saved = flush.flush()
        finally:
            TagPipelineHooks.clear()

        elapsed = time.monotonic() - t0
        return {
            "success": run_ctx.fail == 0,
            "jobs": len(jobs),
            "ok": run_ctx.ok,
            "fail": run_ctx.fail,
            "tag_values_count": run_ctx.tag_values_count,
            "saved_tag_values": saved,
            "elapsed_seconds": elapsed,
            "dry_run": dry_run,
        }


__all__ = ["TagSlicePipeline"]
