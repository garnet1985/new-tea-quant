"""Tag entity_based 编排：JobBuilder → BE.entity_based.run → flush。

消费者: Tag facade / TagManager（迁移后）
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

from core.modules.backtest_engine import BacktestEngine
from core.modules.backtest_engine.contracts import JobReport, RunCallbacks, RunProgress
from core.modules.backtest_engine.core.performance.settings import (
    resolve_entity_based_performance,
)
from core.modules.tag.core.data_class.scenario import Scenario
from core.modules.tag.core.engines.entity_based.executor import TagEntityJobExecutor
from core.modules.tag.core.engines.entity_based.job_builder import TagEntityJobBuilder
from core.modules.tag.core.engines.shared.services.tag_value_flush import (
    TagValueFlushService,
)
from core.modules.tag.core.engines.shared.tag_settings.tag_settings import TagSettings
from core.modules.tag.core.services.discovery.data.discovered_tag import EnabledTagInfo
from core.modules.tag.settings.worker_profile import profile_tag_entity_based_config

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
        shm_info: Optional[Dict[str, Any]] = None,
        dry_run: bool = False,
        save_batch_size: int = 500,
        on_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        settings = TagSettings.from_dict(
            dict(scenario.settings or {}),
            tag_key=scenario.name,
        )
        settings.apply_defaults()
        period = settings.resolve_period()

        jobs = TagEntityJobBuilder.build_backtest_engine_jobs(
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
        performance = resolve_entity_based_performance(
            profile_tag_entity_based_config()
        )

        finished = 0
        ok = 0
        fail = 0
        tag_values_count = 0
        t0 = time.monotonic()

        def on_task_result(report: JobReport, progress: RunProgress) -> None:
            nonlocal finished, ok, fail, tag_values_count
            finished += 1
            if report.success:
                ok += 1
            else:
                fail += 1
            data = report.data if isinstance(report.data, dict) else {}
            rows = data.get("tag_values") or []
            if rows:
                tag_values_count += flush.extend(rows)
            if on_progress is not None:
                on_progress(
                    {
                        "finished": finished,
                        "total": max(len(jobs), 1),
                        "ok": ok,
                        "fail": fail,
                        "progress_pct": min(
                            100.0, finished / max(len(jobs), 1) * 100.0
                        ),
                    }
                )

        base_cb = TagEntityJobExecutor.build_run_callbacks()
        callbacks = RunCallbacks(
            on_before_task_start=base_cb.on_before_task_start,
            on_tick=base_cb.on_tick,
            on_ticks_complete=base_cb.on_ticks_complete,
            on_task_result=on_task_result,
        )

        logger.info(
            "TagEntityPipeline start: scenario=%s entities=%d jobs=%d dry_run=%s",
            scenario.name,
            len(entity_ids),
            len(jobs),
            dry_run,
        )
        BacktestEngine.entity_based.run(
            jobs=jobs,
            start=period.start_date,
            end=period.end_date,
            performance=performance,
            callbacks=callbacks,
            task_name=f"tag:{scenario.name}",
        )
        saved = flush.flush()
        elapsed = time.monotonic() - t0
        return {
            "success": fail == 0,
            "jobs": len(jobs),
            "ok": ok,
            "fail": fail,
            "tag_values_count": tag_values_count,
            "saved_tag_values": saved,
            "elapsed_seconds": elapsed,
            "dry_run": dry_run,
        }


__all__ = ["TagEntityPipeline"]
