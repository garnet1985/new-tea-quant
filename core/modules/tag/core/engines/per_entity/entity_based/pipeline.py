"""Tag entity_based 编排：JobBuilder → BE.entity_based.run → flush。

消费者: Tag facade
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

from core.modules.backtest_engine import BacktestEngine
from core.modules.backtest_engine.contracts import RunCallbacks
from core.modules.backtest_engine.core.performance.settings import (
    resolve_entity_based_performance,
)
from core.modules.tag.core.data_class.scenario import Scenario
from core.modules.tag.core.engines.per_entity.entity_based.executor import TagEntityJobExecutor
from core.modules.tag.core.engines.per_entity.entity_based.job_builder import TagEntityJobBuilder
from core.modules.tag.core.engines.per_entity.shared.pipeline_hooks import (
    TagPipelineHooks,
    TagPipelineRunContext,
)
from core.modules.tag.core.engines.per_entity.shared.services.tag_value_flush import (
    TagValueFlushService,
)
from core.modules.tag.core.engines.per_entity.shared.tag_settings.tag_settings import TagSettings
from core.modules.tag.core.enums import TagUpdateMode
from core.modules.tag.core.services.discovery.data.discovered_tag import EnabledTagInfo
from core.modules.tag.core.engines.per_entity.shared.worker_profile import TagWorkerProfile

if TYPE_CHECKING:
    from core.modules.data_manager.data_services.stock.sub_services.tag_service import (
        TagDataService,
    )

logger = logging.getLogger(__name__)


class TagEntityPipeline:
    """entity_based Tag 计算编排。"""

    @classmethod
    def run(
        cls,
        *,
        tag_info: EnabledTagInfo,
        scenario: Scenario,
        entity_ids: List[str],
        tag_data_service: Optional["TagDataService"] = None,
        dry_run: bool = False,
        save_batch_size: int = 500,
        on_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        settings = TagSettings.from_dict(
            dict(scenario.settings or {}),
            tag_key=scenario.name,
        )
        settings.apply_defaults()

        jobs = TagEntityJobBuilder.build_backtest_engine_jobs(
            tag_info,
            scenario,
            entity_ids,
            tag_data_service=tag_data_service,
        )
        if not jobs:
            return {
                "success": True,
                "jobs": 0,
                "saved_tag_values": 0,
                "tag_values_count": 0,
                "message": "no jobs",
            }

        run_start = str(jobs[0]["payload"].get("start_date") or "").strip()
        run_end = str(jobs[0]["payload"].get("end_date") or "").strip()
        if not run_start or not run_end:
            period = settings.resolve_period()
            run_start = period.start_date
            run_end = period.end_date

        flush = TagValueFlushService(
            tag_data_service,
            dry_run=dry_run,
            batch_size=save_batch_size,
        )
        performance = resolve_entity_based_performance(
            TagWorkerProfile.entity_based()
        )
        run_ctx = TagPipelineRunContext(
            flush=flush,
            total_jobs=len(jobs),
            on_progress=on_progress,
        )
        TagPipelineHooks.bind(run_ctx)
        t0 = time.monotonic()
        saved = 0
        try:
            base_cb = TagEntityJobExecutor.build_run_callbacks()
            callbacks = RunCallbacks(
                on_before_task_start=base_cb.on_before_task_start,
                on_tick=base_cb.on_tick,
                on_ticks_complete=base_cb.on_ticks_complete,
                on_task_result=TagPipelineHooks.on_task_result,
            )

            logger.info(
                "TagEntityPipeline start: scenario=%s entities=%d jobs=%d "
                "period=%s—%s dry_run=%s",
                scenario.name,
                len(entity_ids),
                len(jobs),
                run_start,
                run_end,
                dry_run,
            )
            BacktestEngine.entity_based.run(
                jobs=jobs,
                start=run_start,
                end=run_end,
                performance=performance,
                callbacks=callbacks,
                task_name=f"tag:{scenario.name}",
            )
            saved = flush.flush()
        finally:
            TagPipelineHooks.clear()

        elapsed = time.monotonic() - t0
        success = run_ctx.fail == 0
        if (
            success
            and (not dry_run)
            and scenario.effective_update_mode() == TagUpdateMode.INCREMENTAL.value
        ):
            # incremental 水位 = 本次成功算到的业务 end（非 max(as_of)）
            entity_ends: Dict[str, str] = {}
            for item in jobs[0]["payload"].get("entity_specified") or []:
                if not isinstance(item, dict):
                    continue
                eid = str(item.get("id") or "").strip()
                end = str(item.get("end_date") or run_end or "").strip()
                if eid and end:
                    entity_ends[eid] = end
            if entity_ends and tag_data_service is not None:
                tag_data_service.mark_entity_calc_progress(
                    scenario.name, entity_ends
                )
                logger.info(
                    "incremental progress saved: scenario=%s entities=%d end≈%s",
                    scenario.name,
                    len(entity_ends),
                    run_end,
                )
            elif entity_ends and tag_data_service is None:
                logger.warning(
                    "incremental progress skipped (no tag_data_service): scenario=%s",
                    scenario.name,
                )
        return {
            "success": success,
            "jobs": len(jobs),
            "ok": run_ctx.ok,
            "fail": run_ctx.fail,
            "tag_values_count": run_ctx.tag_values_count,
            "saved_tag_values": saved,
            "elapsed_seconds": elapsed,
            "dry_run": dry_run,
        }


__all__ = ["TagEntityPipeline"]
