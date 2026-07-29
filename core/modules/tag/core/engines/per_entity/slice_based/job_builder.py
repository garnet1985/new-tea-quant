"""slice_based TagSliceJobBuilder — 为 BE 组装 jobs。

消费者: TagSlicePipeline

本文件:
- TagSliceJobBuilder: payload + ``timeline_point_count``；
  incremental 时按 ``sys_tag_calc_progress`` 裁窗
  边界: 喂 jobs；点数用 ``Timeline.from_calendar_window``；不负责执行
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from core.modules.backtest_engine.contracts import Timeline
from core.modules.backtest_engine.core.shared.jobs import BacktestJob
from core.modules.tag.core.data_class.scenario import Scenario
from core.modules.tag.core.engines.shared.calc_window import TagCalcWindowResolver
from core.modules.tag.core.engines.per_entity.shared.job_payload import TagJobPayloadBuilder
from core.modules.tag.core.engines.shared.tag_settings.tag_settings import TagSettings
from core.modules.tag.core.services.discovery.data.discovered_tag import DiscoveredTagInfo

if TYPE_CHECKING:
    from core.modules.data_manager.data_services.stock.sub_services.tag_service import (
        TagDataService,
    )

logger = logging.getLogger(__name__)


class TagSliceJobBuilder:
    """slice_based Tag Job 构建。"""

    @classmethod
    def build_backtest_engine_jobs(
        cls,
        tag_info: DiscoveredTagInfo,
        scenario: Scenario,
        entity_ids: List[str],
        *,
        tag_data_service: Optional["TagDataService"] = None,
    ) -> List[Dict[str, Any]]:
        settings = TagSettings.from_dict(
            dict(scenario.settings or {}),
            tag_key=scenario.name,
        )
        settings.apply_defaults()
        windows = TagCalcWindowResolver.resolve(
            scenario=scenario,
            settings=settings,
            entity_ids=entity_ids,
            tag_data_service=tag_data_service,
        )
        if not windows.entities:
            logger.info(
                "TagSliceJobBuilder: 无待算实体（skipped_up_to_date=%d），跳过 job",
                windows.skipped_up_to_date,
            )
            return []

        point_count = cls._count_open_dates(windows.data_start, windows.data_end)
        payload = TagJobPayloadBuilder.build_core_payload(
            tag_info=tag_info,
            scenario=scenario,
            settings=settings,
            entity_ids=entity_ids,
            start_date=windows.data_start,
            end_date=windows.data_end,
            calc_windows=windows,
        )
        if not payload.get("entity_specified"):
            logger.warning("TagSliceJobBuilder: entity_specified 为空，跳过 job")
            return []

        ids = [item["id"] for item in payload["entity_specified"]]
        payload[BacktestJob.SLICE_BASED_ENTITY_KEY] = list(ids)
        payload[BacktestJob.TIMELINE_POINT_COUNT_KEY] = point_count
        payload.pop(Timeline.PAYLOAD_KEY, None)

        logger.info(
            "TagSliceJobBuilder: entity_count=%d timeline_point_count=%d "
            "period=%s—%s update_mode=%s skipped=%d",
            len(ids),
            point_count,
            payload.get("start_date"),
            payload.get("end_date"),
            payload.get("update_mode"),
            windows.skipped_up_to_date,
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
