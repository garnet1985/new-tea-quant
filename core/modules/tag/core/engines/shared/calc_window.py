"""Tag 计算窗口解析（incremental / refresh）。

消费者: TagEntityJobBuilder

incremental：从 DB ``sys_tag_calc_progress`` 取 entity → last_calculated_end map，
再对 list 内实体裁窗（start = end+1）；无行则从 settings 起点。
refresh：全员使用 settings 默认窗。

水位 API（``TagDataService``）：``get_entity_calc_progress`` /
``mark_entity_calc_progress`` / ``clear_calc_progress_by_scenario``。

注意：不要用 max(as_of_date) 当水位——变化日写入的 tag 的 as_of
只表示最近一次落库结果日，不等于计算推进到的日期。
``calculated_at`` / scenario.updated_at 是墙钟/元数据时间，同样不能当水位。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.modules.tag.core.data_class.scenario import Scenario
from core.modules.tag.core.engines.shared.tag_settings.tag_settings import TagSettings
from core.modules.tag.core.enums import TagUpdateMode
from core.infra.utils import Utils
logger = logging.getLogger(__name__)


@dataclass
class EntityCalcWindow:
    entity_id: str
    start_date: str
    end_date: str

    @property
    def is_empty(self) -> bool:
        start = str(self.start_date or "").strip()
        end = str(self.end_date or "").strip()
        return (not start) or (not end) or start > end


@dataclass
class TagCalcWindows:
    """全 job 数据装载窗 + 每实体计算窗。"""

    data_start: str
    data_end: str
    entities: List[EntityCalcWindow] = field(default_factory=list)
    skipped_up_to_date: int = 0

    @property
    def entity_ids(self) -> List[str]:
        return [e.entity_id for e in self.entities]


class TagCalcWindowResolver:
    """根据 update_mode / DB 计算进度水位解析计算窗。"""

    @classmethod
    def resolve(
        cls,
        *,
        scenario: Scenario,
        settings: TagSettings,
        entity_ids: List[str],
        tag_data_service: Optional[Any] = None,
    ) -> TagCalcWindows:
        period = settings.resolve_period()
        default_start = str(period.start_date or "").strip()
        default_end = str(period.end_date or "").strip()
        ids = [str(eid).strip() for eid in entity_ids if str(eid).strip()]

        mode = str(
            scenario.effective_update_mode() or TagUpdateMode.INCREMENTAL.value
        ).strip().lower()

        if mode != TagUpdateMode.INCREMENTAL.value:
            entities = [
                EntityCalcWindow(
                    entity_id=eid, start_date=default_start, end_date=default_end
                )
                for eid in ids
            ]
            return TagCalcWindows(
                data_start=default_start,
                data_end=default_end,
                entities=entities,
            )

        progress = cls._load_progress_map(tag_data_service, scenario.name)
        entities: List[EntityCalcWindow] = []
        skipped = 0
        for eid in ids:
            last_calculated_end = str(progress.get(eid) or "").strip()
            start, end = cls._incremental_range(
                last_calculated_end=last_calculated_end,
                default_start=default_start,
                default_end=default_end,
            )
            window = EntityCalcWindow(entity_id=eid, start_date=start, end_date=end)
            if window.is_empty:
                skipped += 1
                continue
            entities.append(window)

        if not entities:
            logger.info(
                "incremental: 全部 %d 个实体已追上 end=%s（按 last_calculated_end），无待算窗口",
                len(ids),
                default_end,
            )
            return TagCalcWindows(
                data_start=default_start,
                data_end=default_end,
                entities=[],
                skipped_up_to_date=skipped,
            )

        data_start = min(e.start_date for e in entities)
        data_end = max(e.end_date for e in entities)
        logger.info(
            "incremental: active=%d skipped_up_to_date=%d data_window=%s—%s "
            "(watermark=last_calculated_end, not max(as_of))",
            len(entities),
            skipped,
            data_start,
            data_end,
        )
        return TagCalcWindows(
            data_start=data_start,
            data_end=data_end,
            entities=entities,
            skipped_up_to_date=skipped,
        )

    @classmethod
    def _load_progress_map(
        cls,
        tag_data_service: Optional[Any],
        scenario_name: str,
    ) -> Dict[str, str]:
        if tag_data_service is None:
            logger.warning(
                "incremental: tag_data_service missing，无 progress map，"
                "全部实体从 settings 起点算: %s",
                scenario_name,
            )
            return {}
        raw = tag_data_service.get_entity_calc_progress(scenario_name)
        if not isinstance(raw, dict):
            return {}
        out: Dict[str, str] = {}
        for eid, end in raw.items():
            key = str(eid or "").strip()
            val = str(end or "").strip()
            if key and val:
                out[key] = val
        return out

    @classmethod
    def _incremental_range(
        cls,
        *,
        last_calculated_end: str,
        default_start: str,
        default_end: str,
    ) -> tuple[str, str]:
        end = str(default_end or "").strip()
        if last_calculated_end:
            start = Utils.date.add_days(str(last_calculated_end).strip(), 1)
        else:
            start = str(default_start or "").strip()
        return start, end


__all__ = ["TagCalcWindowResolver"]
