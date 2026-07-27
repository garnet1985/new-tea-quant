#!/usr/bin/env python3
"""Tag calendar_slice dispatch job 构建。"""

from __future__ import annotations

from typing import Any, Dict, List

from core.modules.tag.enums import TagExecutionMode, TagUpdateMode
from core.modules.tag.models.scenario_model import ScenarioModel


def build_tag_calendar_slice_job(
    *,
    entity_ids: List[str],
    settings: Dict[str, Any],
    scenario_model: ScenarioModel,
    worker_module_path: str,
    worker_class_name: str,
    worker_file_path: str = "",
    global_extra_cache: Dict[str, Any],
) -> Dict[str, Any]:
    ids = [str(e).strip() for e in entity_ids if str(e).strip()]
    if not ids:
        raise ValueError("slice_based tag job 需要非空 entity_ids")

    start_date = str(settings.get("start_date") or "")
    end_date = str(settings.get("end_date") or "")
    tag_target_type = str(settings.get("tag_target_type") or "entity_based").strip().lower()
    entity_type = (
        "general"
        if tag_target_type == "general"
        else str(scenario_model.get_target_entity() or "stock")
    )
    tag_models = scenario_model.get_tag_models()
    tag_definitions = [tag_model.to_dict() for tag_model in tag_models]
    update_mode = scenario_model.calculate_update_mode()
    if update_mode != TagUpdateMode.REFRESH:
        raise ValueError("slice_based tag 当前仅支持 REFRESH 模式")

    entities = [
        {"entity_id": eid, "start_date": start_date, "end_date": end_date}
        for eid in ids
    ]
    scenario_name = scenario_model.get_name()
    return {
        "tag_execution_mode": TagExecutionMode.SLICE_BASED.value,
        "slice_open_days": "auto",
        "entity_ids": ids,
        "entities": entities,
        "entity_type": entity_type,
        "scenario_name": scenario_name,
        "update_mode": update_mode,
        "tag_definitions": tag_definitions,
        "settings": settings,
        "start_date": start_date,
        "end_date": end_date,
        "worker_module_path": worker_module_path,
        "worker_class_name": worker_class_name,
        "worker_file_path": str(worker_file_path or ""),
        "global_extra_cache": global_extra_cache,
    }


__all__ = ["build_tag_calendar_slice_job"]
