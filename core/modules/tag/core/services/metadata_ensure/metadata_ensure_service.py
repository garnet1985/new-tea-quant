"""Metadata ensure — 将 Scenario / TagDefinition 同步到 DB。

消费者: Tag facade / 后续 engines（跑计算前）

本文件:
- MetadataEnsureService: scenario + tag_definition 的 create/update/recompute/refresh
  边界: 负责元数据与 tag_value 清理策略；不负责 discovery、settings 校验或打标计算
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Optional

from core.modules.tag.core.data_class.scenario import Scenario
from core.modules.tag.core.data_class.tag_definition import TagDefinition
from core.modules.tag.core.enums import TagUpdateMode

if TYPE_CHECKING:
    from core.modules.data_manager.data_services.stock.sub_services.tag_service import (
        TagDataService,
    )

logger = logging.getLogger(__name__)


class MetadataEnsureService:
    """确保 scenario / tag_definition 元数据存在且与 settings 对齐。"""

    def __init__(self, tag_data_service: "TagDataService") -> None:
        if tag_data_service is None:
            raise ValueError("tag_data_service is required")
        self._tags = tag_data_service

    def ensure(self, scenario: Scenario) -> Scenario:
        """Ensure scenario 及其 tag_definitions；就地更新 id / 时间戳后返回同一实例。"""
        if not isinstance(scenario, Scenario):
            raise TypeError("scenario must be Scenario")
        if not str(scenario.name or "").strip():
            raise ValueError("scenario.name is required")

        self.ensure_scenario(scenario)
        self.ensure_tag_definitions(scenario)
        return scenario

    def ensure_scenario(self, scenario: Scenario) -> None:
        """同步 ``sys_tag_scenario``；recompute 时重建；refresh 时清 tag values。"""
        existing = self._tags.load_scenario(scenario.name)

        if not existing:
            new_meta = self._tags.save_scenario(
                scenario.name,
                display_name=scenario.display_name or scenario.name,
                description=scenario.description or "",
            )
            scenario.apply_db_meta(new_meta or {})
            return

        scenario_id = TagDefinition._optional_int(existing.get("id"))
        if scenario_id is None:
            raise ValueError(f"DB scenario missing id: {scenario.name!r}")

        if scenario.recompute:
            logger.info(
                "recompute=True, recreate scenario metadata: %s", scenario.name
            )
            self._tags.delete_tag_values_by_scenario(scenario_id)
            self._tags.delete_tag_definitions_by_scenario(scenario_id)
            self._tags.delete_scenario(scenario_id, cascade=False)
            new_meta = self._tags.save_scenario(
                scenario.name,
                display_name=scenario.display_name or scenario.name,
                description=scenario.description or "",
            )
            scenario.apply_db_meta(new_meta or {})
            return

        if scenario.effective_update_mode() == TagUpdateMode.REFRESH.value:
            logger.info(
                "update_mode=refresh, clear tag values: %s", scenario.name
            )
            self._tags.delete_tag_values_by_scenario(scenario_id)

        if scenario.has_meta_diff(existing):
            new_meta = self._tags.update_scenario(
                scenario_id,
                display_name=scenario.display_name or scenario.name,
                description=scenario.description or "",
                current_scenario=existing,
            )
            scenario.apply_db_meta(new_meta or existing)
        else:
            scenario.apply_db_meta(existing)

    def ensure_tag_definitions(self, scenario: Scenario) -> None:
        """同步 scenario 下全部 ``sys_tag_definition``。"""
        scenario_id = scenario.id
        if scenario_id is None:
            raise ValueError(
                f"scenario.id missing before ensuring tag definitions: {scenario.name!r}"
            )

        for definition in scenario.tag_definitions:
            self.ensure_tag_definition(
                definition,
                scenario_id=scenario_id,
                recompute=scenario.recompute,
            )

    def ensure_tag_definition(
        self,
        definition: TagDefinition,
        *,
        scenario_id: int,
        recompute: bool = False,
    ) -> TagDefinition:
        """同步单条 tag definition；就地更新后返回。"""
        if not isinstance(definition, TagDefinition):
            raise TypeError("definition must be TagDefinition")
        name = str(definition.name or "").strip()
        if not name:
            raise ValueError("TagDefinition.name is required")

        definition.scenario_id = int(scenario_id)
        display_name = definition.display_name or name
        description = definition.description or ""

        existing = self._tags.load(name, scenario_id)

        if recompute:
            if existing:
                existing_id = TagDefinition._optional_int(existing.get("id"))
                if existing_id is not None:
                    self._tags.delete_tag_definition(existing_id)
            new_meta = self._tags.save(
                name, scenario_id, display_name, description
            )
            definition.apply_db_meta(new_meta or {})
            return definition

        if not existing:
            new_meta = self._tags.save(
                name, scenario_id, display_name, description
            )
            definition.apply_db_meta(new_meta or {})
            return definition

        if definition.has_meta_diff(existing):
            existing_id = TagDefinition._optional_int(existing.get("id"))
            if existing_id is None:
                raise ValueError(f"DB tag definition missing id: {name!r}")
            new_meta = self._tags.update_tag_definition(
                existing_id,
                display_name=display_name,
                description=description,
                current_tag=existing,
            )
            definition.apply_db_meta(new_meta or existing)
        else:
            definition.apply_db_meta(existing)

        return definition


__all__ = ["MetadataEnsureService"]
