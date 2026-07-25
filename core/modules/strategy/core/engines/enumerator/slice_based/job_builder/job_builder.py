"""slice_based JobBuilder — 为 BE 组装 jobs。

本文件（slice 两件套之一，与 Executor）:
- JobBuilder: 基类 payload + entity_ids + timeline_point_count（规划用，非推进轴复写）
  边界: 负责 slice job payload；推进轴交给 BE 默认日历
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from core.modules.backtest_engine.contracts import Timeline
from core.modules.backtest_engine.core.shared.jobs import BacktestJob
from core.modules.strategy.core.engines.enumerator.shared.base_job_builder import (
    BaseJobBuilder,
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
    - 负责: 基类 payload + entity_ids + ``timeline_point_count``（BE 规划切片规模）
    - 不负责: 覆盖 BE Timeline.points；执行、报告落盘
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
        point_count = cls._count_open_dates(start_date, end_date)

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
        # 规划用 point 计数；禁止把全量 points 塞进 payload（由 BE 日历轴驱动）
        payload[BacktestJob.TIMELINE_POINT_COUNT_KEY] = point_count
        payload.pop(Timeline.PAYLOAD_KEY, None)
        logger.info(
            "slice JobBuilder: entity_count=%d, timeline_point_count=%d",
            len(ids),
            point_count,
        )
        return [{"id": "strategy_run", "payload": payload}]

    @classmethod
    def _count_open_dates(cls, start_date: str, end_date: str) -> int:
        """BE 规划用：与 Timeline.from_calendar_window 同源，只取点数。"""
        points = Timeline.from_calendar_window(start_date, end_date).points
        if not points:
            raise ValueError(
                f"slice JobBuilder: 回测窗 {start_date}—{end_date} 无开市日，"
                "无法规划 timeline_point_count"
            )
        return len(points)


__all__ = ["JobBuilder"]
