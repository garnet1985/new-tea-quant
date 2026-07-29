"""entity_based TagEntityJobBuilder — 为 BE 组装 jobs。

消费者: TagEntityPipeline

本文件:
- TagEntityJobBuilder: 复用核心 payload；incremental 按 last_calculated_end 裁窗，
  并预取 prior tag 值供变化检测暖启动
  边界: 喂 jobs；推进轴交给 BE 默认日历
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from core.modules.tag.core.data_class.scenario import Scenario
from core.modules.tag.core.engines.shared.calc_window import TagCalcWindowResolver
from core.modules.tag.core.engines.per_entity.shared.job_payload import TagJobPayloadBuilder
from core.modules.tag.core.engines.shared.prior_values import TagPriorValues
from core.modules.tag.core.engines.shared.tag_settings.tag_settings import TagSettings
from core.modules.tag.core.enums import TagUpdateMode
from core.modules.tag.core.services.discovery.data.discovered_tag import DiscoveredTagInfo

if TYPE_CHECKING:
    from core.modules.data_manager.data_services.stock.sub_services.tag_service import (
        TagDataService,
    )

logger = logging.getLogger(__name__)


class TagEntityJobBuilder:
    """entity_based Tag Job 构建。"""

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
            logger.info(
                "TagEntityJobBuilder: 无待算实体（skipped_up_to_date=%d），跳过 job",
                windows.skipped_up_to_date,
            )
            return []

        if (
            scenario.effective_update_mode() == TagUpdateMode.INCREMENTAL.value
            and tag_data_service is not None
        ):
            payload["prior_tag_values"] = cls._load_prior_tag_values(
                tag_data_service,
                scenario=scenario,
                entity_ids=list(payload.get("entity_specified") or []),
            )

        logger.info(
            "TagEntityJobBuilder: entity_count=%d period=%s—%s update_mode=%s skipped=%d",
            len(payload["entity_specified"]),
            payload.get("start_date"),
            payload.get("end_date"),
            payload.get("update_mode"),
            windows.skipped_up_to_date,
        )
        return [{"id": "tag_run", "payload": payload}]

    @classmethod
    def _load_prior_tag_values(
        cls,
        tag_data_service: "TagDataService",
        *,
        scenario: Scenario,
        entity_ids: List[Any],
    ) -> Dict[str, Dict[str, Any]]:
        ids: List[str] = []
        for item in entity_ids:
            if isinstance(item, dict):
                eid = str(item.get("id") or "").strip()
            else:
                eid = str(item or "").strip()
            if eid:
                ids.append(eid)
        def_ids = [
            int(d.id)
            for d in scenario.tag_definitions
            if d.id is not None
        ]
        name_by_id = {
            str(int(d.id)): str(d.name)
            for d in scenario.tag_definitions
            if d.id is not None and d.name
        }
        if not ids or not def_ids:
            return {}
        raw = TagPriorValues.fetch_batch(
            tag_data_service,
            entity_ids=ids,
            tag_definition_ids=def_ids,
        )
        out: Dict[str, Dict[str, Any]] = {}
        for eid, by_def in (raw or {}).items():
            parsed: Dict[str, Any] = {}
            for def_id, json_value in (by_def or {}).items():
                scalar = TagPriorValues.parse_scalar(json_value)
                if scalar is None:
                    continue
                key = str(def_id)
                parsed[key] = scalar
                tag_name = name_by_id.get(key)
                if tag_name:
                    parsed[tag_name] = scalar
            if parsed:
                out[str(eid)] = parsed
        return out


__all__ = ["TagEntityJobBuilder"]
