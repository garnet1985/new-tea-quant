#!/usr/bin/env python3
"""slice_based Job 构建：公共 payload + BE.slice_based 契约字段。"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from core.modules.strategy.core.engines.enumerator.shared.services.job_payload import (
    JobPayloadBuilder,
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


class JobBuilder:
    """slice_based Job 构建（无状态）。

    边界:
    - 负责: JobPayloadBuilder 公共主体 + open_dates / backtest_calendar / stock_ids
    - 不负责: 执行、报告落盘
    - 调用方: EnumeratorPipeline
    """

    @staticmethod
    def build_backtest_engine_jobs(
        strategy_info: EnabledStrategyInfo,
        effective_settings: StrategySettings,
        entity_ids: List[str],
        global_declarations: List[Dict[str, Any]],
        per_entity_declarations: List[Dict[str, Any]],
        shm_info: Dict[str, Any],
        output_recorder_snapshot: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        period = JobPayloadBuilder.resolve_period(effective_settings)
        start_date = period.start_date
        end_date = period.end_date

        open_dates, calendar_dict = BacktestCalendarResolver.resolve(
            settings=effective_settings.raw_settings,
            start_date=start_date,
            end_date=end_date,
        )

        payload = JobPayloadBuilder.build_core_payload(
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
            payload.update(
                {
                    "stock_ids": [],
                    "entity_ids": [],
                    "open_dates": [],
                }
            )
            return [{"id": "strategy_run", "payload": payload}]

        ids = [item["id"] for item in payload["entity_specified"]]
        payload.update(
            {
                "stock_ids": list(ids),
                "entity_ids": list(ids),
                "open_dates": list(open_dates),
                "backtest_calendar": dict(calendar_dict),
                "start_date": start_date,
                "end_date": end_date,
            }
        )
        logger.info(
            "slice JobBuilder 补齐契约字段：entity_count=%d, open_dates=%d",
            len(ids),
            len(open_dates),
        )
        return [{"id": "strategy_run", "payload": payload}]


__all__ = ["JobBuilder"]
