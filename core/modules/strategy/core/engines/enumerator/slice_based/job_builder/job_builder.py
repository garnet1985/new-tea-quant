#!/usr/bin/env python3
"""slice_based Job 构建：公共 payload + BE.slice_based 契约字段。"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from core.modules.backtest_engine.core.shared.jobs import BacktestJob
from core.modules.strategy.core.engines.enumerator.shared.base_job_builder import (
    BaseJobBuilder,
)
from core.modules.strategy.core.engines.enumerator.shared.services.enumerator_timeline import (
    EnumeratorTimeline,
)
from core.modules.strategy.core.engines.enumerator.slice_based.resolver.calendar import (
    BacktestCalendarResolver,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.services.discovery.data.discovered_strategy import (
    EnabledStrategyInfo,
)

logger = logging.getLogger(__name__)


class JobBuilder(BaseJobBuilder):
    """slice_based Job 构建。

    边界:
    - 负责: 基类 payload + entity_ids + timeline_point_count（全量 points 不进 payload）
    - 不负责: 执行、报告落盘；Timeline 由 worker 从全局 trade.calendar 解析
    - 调用方: EnumeratorPipeline
    """

    @classmethod
    def build_backtest_engine_jobs(
        cls,
        strategy_info: EnabledStrategyInfo,
        effective_settings: StrategySettings,
        entity_ids: List[str],
        global_declarations: List[Dict[str, Any]],
        per_entity_declarations: List[Dict[str, Any]],
        shm_info: Dict[str, Any],
        output_recorder_snapshot: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        period = cls._resolve_period(effective_settings)
        start_date = period.start_date
        end_date = period.end_date

        open_points, calendar_dict = BacktestCalendarResolver.resolve(
            settings=effective_settings.raw_settings,
            start_date=start_date,
            end_date=end_date,
        )
        if not open_points:
            raise ValueError("slice JobBuilder: open_points 为空，无法规划 timeline_point_count")

        payload = cls._build_core_payload(
            strategy_info=strategy_info,
            effective_settings=effective_settings,
            entity_ids=entity_ids,
            global_declarations=global_declarations,
            per_entity_declarations=per_entity_declarations,
            shm_info=shm_info,
            start_date=start_date,
            end_date=end_date,
            output_recorder_snapshot=output_recorder_snapshot,
        )
        if not payload.get("entity_specified"):
            logger.warning("slice JobBuilder: entity_specified 为空，跳过 job")
            return []

        ids = [item["id"] for item in payload["entity_specified"]]
        payload[BacktestJob.SLICE_BASED_ENTITY_KEY] = list(ids)
        payload["start_date"] = start_date
        payload["end_date"] = end_date
        EnumeratorTimeline.bind_point_count(payload, len(open_points))
        logger.info(
            "slice JobBuilder: entity_count=%d, timeline_point_count=%d, market=%s",
            len(ids),
            len(open_points),
            calendar_dict.get("market"),
        )
        return [{"id": "strategy_run", "payload": payload}]


__all__ = ["JobBuilder"]
