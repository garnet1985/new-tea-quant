"""slice_based TagSliceJobBuilder — 为 BE 组装 jobs。

消费者: TagSlicePipeline

本文件:
- TagSliceJobBuilder: payload + ``timeline_point_count``
  边界: 喂 jobs；点数用 ``Timeline.from_calendar_window``；不负责执行
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from core.modules.backtest_engine.contracts import Timeline
from core.modules.backtest_engine.core.shared.jobs import BacktestJob
from core.modules.tag.core.data_class.scenario import Scenario
from core.modules.tag.core.engines.shared.job_payload import TagJobPayloadBuilder
from core.modules.tag.core.engines.shared.tag_settings.tag_settings import TagSettings
from core.modules.tag.core.services.discovery.data.discovered_tag import EnabledTagInfo

logger = logging.getLogger(__name__)


class TagSliceJobBuilder:
    """slice_based Tag Job 构建。"""

    @classmethod
    def build_backtest_engine_jobs(
        cls,
        tag_info: EnabledTagInfo,
        scenario: Scenario,
        entity_ids: List[str],
        shm_info: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        settings = TagSettings.from_dict(
            dict(scenario.settings or {}),
            tag_key=scenario.name,
        )
        settings.apply_defaults()
        period = settings.resolve_period()
        start_date = period.start_date
        end_date = period.end_date
        point_count = cls._count_open_dates(start_date, end_date)

        payload = TagJobPayloadBuilder.build_core_payload(
            tag_info=tag_info,
            scenario=scenario,
            settings=settings,
            entity_ids=entity_ids,
            shm_info=shm_info or {},
            start_date=start_date,
            end_date=end_date,
        )
        if not payload.get("entity_specified"):
            logger.warning("TagSliceJobBuilder: entity_specified 为空，跳过 job")
            return []

        ids = [item["id"] for item in payload["entity_specified"]]
        payload[BacktestJob.SLICE_BASED_ENTITY_KEY] = list(ids)
        payload[BacktestJob.TIMELINE_POINT_COUNT_KEY] = point_count
        payload.pop(Timeline.PAYLOAD_KEY, None)

        logger.info(
            "TagSliceJobBuilder: entity_count=%d, timeline_point_count=%d",
            len(ids),
            point_count,
        )
        return [{"id": "tag_run", "payload": payload}]

    @classmethod
    def _count_open_dates(cls, start_date: str, end_date: str) -> int:
        points = Timeline.from_calendar_window(start_date, end_date).points
        if not points:
            raise ValueError(
                f"TagSliceJobBuilder: 计算窗 {start_date}—{end_date} 无开市日，"
                "无法规划 timeline_point_count"
            )
        return len(points)


__all__ = ["TagSliceJobBuilder"]
