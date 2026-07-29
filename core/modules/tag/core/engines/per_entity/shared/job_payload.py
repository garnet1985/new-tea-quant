"""Tag job payload 公共组装（entity / slice 共用）。

消费者: TagSliceJobBuilder, TagEntityJobBuilder
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.modules.tag.core.data_class.scenario import Scenario
from core.modules.tag.core.engines.per_entity.shared.calc_window import (
    EntityCalcWindow,
    TagCalcWindows,
)
from core.modules.tag.core.engines.per_entity.shared.tag_settings.data_settings import DataSettings
from core.modules.tag.core.engines.per_entity.shared.tag_settings.tag_settings import TagSettings
from core.modules.tag.core.services.discovery.data.discovered_tag import DiscoveredTagInfo

logger = logging.getLogger(__name__)


class TagJobPayloadBuilder:
    """组装 tag job 核心 payload（供 BacktestEngine）。"""

    @classmethod
    def split_declarations(
        cls, settings: TagSettings
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        decls = settings.data.issue_declarations()
        per_entity: List[Dict[str, Any]] = []
        global_decls: List[Dict[str, Any]] = []
        for item in decls:
            data_key = str(item.get("data_key") or "").strip()
            if not data_key:
                continue
            if DataSettings.is_per_entity(data_key):
                per_entity.append(item)
            else:
                global_decls.append(item)
        return per_entity, global_decls

    @classmethod
    def build_core_payload(
        cls,
        *,
        tag_info: DiscoveredTagInfo,
        scenario: Scenario,
        settings: TagSettings,
        entity_ids: List[str],
        start_date: str,
        end_date: str,
        calc_windows: Optional[TagCalcWindows] = None,
    ) -> Dict[str, Any]:
        if calc_windows is not None:
            entity_windows = list(calc_windows.entities)
            start_date = calc_windows.data_start
            end_date = calc_windows.data_end
        else:
            ids = [str(eid).strip() for eid in entity_ids if str(eid).strip()]
            entity_windows = [
                EntityCalcWindow(
                    entity_id=eid, start_date=start_date, end_date=end_date
                )
                for eid in ids
            ]

        if not entity_windows:
            return {"entity_specified": [], "entity_shared": {}}

        per_entity, global_decls = cls.split_declarations(settings)
        entity_shared: Dict[str, Dict[str, Any]] = {}
        for declaration in per_entity:
            data_key = declaration["data_key"]
            entity_shared[data_key] = {
                "params": declaration.get("params", {}),
                "start": start_date,
                "end": end_date,
                "indicators": declaration.get("indicators", {}),
            }

        global_data_keys: Dict[str, Any] = {
            declaration["data_key"]: {} for declaration in global_decls
        }

        hooks_class_name = tag_info.hooks_class_name
        if not hooks_class_name and tag_info.hooks_class is not None:
            hooks_class_name = tag_info.hooks_class.__name__

        hooks_file = tag_info.hooks_file_path
        if isinstance(hooks_file, Path):
            hooks_file_path = str(hooks_file)
        else:
            hooks_file_path = str(hooks_file or "")

        entity_specified = [
            {
                "id": w.entity_id,
                "start_date": w.start_date,
                "end_date": w.end_date,
            }
            for w in entity_windows
        ]

        return {
            "entity_specified": entity_specified,
            "entity_shared": entity_shared,
            "global": global_data_keys,
            "entities_count": len(entity_specified),
            "tag_info": {
                "key": tag_info.key,
                "unique_relative_path": tag_info.unique_relative_path,
                "hooks_module_path": tag_info.hooks_module_path,
                "hooks_class_name": hooks_class_name,
                "hooks_file_path": hooks_file_path,
            },
            "tag_definitions": [d.to_dict() for d in scenario.tag_definitions],
            "scenario_name": scenario.name,
            "attach_to_data_key": scenario.attach_to_data_key
            or settings.attach_to_data_key,
            "settings": scenario.settings or settings.to_dict(),
            "start_date": start_date,
            "end_date": end_date,
            "update_mode": scenario.effective_update_mode(),
        }


__all__ = ["TagJobPayloadBuilder"]
