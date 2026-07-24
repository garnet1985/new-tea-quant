"""entity_based Job 构建（单 bundle，无 open_dates 进 payload）。

本文件:
- JobBuilder: 复用 BaseJobBuilder 组装 enum payload
  边界: 负责 job 列表；不负责执行、日历解析（slice 侧追加）
"""
from __future__ import annotations

from typing import Any, Dict, List

from core.modules.strategy.core.engines.enumerator.shared.base_job_builder import (
    BaseJobBuilder,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.services.discovery.data.discovered_strategy import (
    EnabledStrategyInfo,
)


class JobBuilder(BaseJobBuilder):
    """entity_based Job 构建。

    边界:
    - 负责: 组装单 bundle job（复用基类 payload）
    - 不负责: 执行、日历 open_dates（slice 侧追加）
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
        payload = cls._build_core_payload(
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
