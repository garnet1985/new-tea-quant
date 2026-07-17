#!/usr/bin/env python3
"""entity_based Job 构建（无状态）。"""
from __future__ import annotations

from typing import Any, Dict, List

from core.modules.strategy.core.engines.enumerator.shared.services.job_payload import (
    JobPayloadBuilder,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.services.discovery.data.discovered_strategy import (
    EnabledStrategyInfo,
)


class JobBuilder:
    """entity_based Job 构建（无状态）。

    边界:
    - 负责: 组装 bundle job（调用 JobPayloadBuilder 公共主体）
    - 不负责: 执行、日历 open_dates（slice 侧额外写入）
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
        payload = JobPayloadBuilder.build_core_payload(
            strategy_info=strategy_info,
            effective_settings=effective_settings,
            entity_ids=entity_ids,
            global_declarations=global_declarations,
            per_entity_declarations=per_entity_declarations,
            shm_info=shm_info,
            start_date=period.start_date,
            end_date=period.end_date,
            output_recorder_snapshot=output_recorder_snapshot,
        )
        return [{"id": "strategy_run", "payload": payload}]


__all__ = ["JobBuilder"]
