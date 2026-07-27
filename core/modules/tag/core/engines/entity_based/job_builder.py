"""entity_based TagEntityJobBuilder — 为 BE 组装 jobs。

消费者: TagEntityPipeline

本文件:
- TagEntityJobBuilder: 复用核心 payload（无 slice 专有字段）
  边界: 喂 jobs；推进轴交给 BE 默认日历
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from core.modules.tag.core.data_class.scenario import Scenario
from core.modules.tag.core.engines.shared.job_payload import TagJobPayloadBuilder
from core.modules.tag.core.engines.shared.tag_settings.tag_settings import TagSettings
from core.modules.tag.core.services.discovery.data.discovered_tag import EnabledTagInfo

logger = logging.getLogger(__name__)


class TagEntityJobBuilder:
    """entity_based Tag Job 构建。"""

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
        payload = TagJobPayloadBuilder.build_core_payload(
            tag_info=tag_info,
            scenario=scenario,
            settings=settings,
            entity_ids=entity_ids,
            shm_info=shm_info or {},
            start_date=period.start_date,
            end_date=period.end_date,
        )
        if not payload.get("entity_specified"):
            logger.warning("TagEntityJobBuilder: entity_specified 为空，跳过 job")
            return []
        logger.info(
            "TagEntityJobBuilder: entity_count=%d period=%s—%s",
            len(payload["entity_specified"]),
            period.start_date,
            period.end_date,
        )
        return [{"id": "tag_run", "payload": payload}]


__all__ = ["TagEntityJobBuilder"]
