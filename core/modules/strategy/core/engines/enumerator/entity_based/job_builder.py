"""entity_based EnumEntityJobBuilder — 为 BE 组装 jobs。

本文件（entity 两件套之一，与 Executor）:
- EnumEntityJobBuilder: 复用 BaseJobBuilder 组装 enum payload
  边界: 负责 job 列表与数据加载窗；推进轴交给 BE 默认日历
"""
from __future__ import annotations

from typing import Any, Dict, List

from core.modules.strategy.core.engines.enumerator.common.base_job_builder import (
    BaseJobBuilder,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.services.discovery.data.discovered_strategy import (
    EnabledStrategyInfo,
)


class EnumEntityJobBuilder(BaseJobBuilder):
    """entity_based Job 构建。

    边界:
    - 负责: 组装单 bundle job（payload 起止来自 settings period）
    - 不负责: 覆盖 BE Timeline.points；执行
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


__all__ = ["EnumEntityJobBuilder"]
