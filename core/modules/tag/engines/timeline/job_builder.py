"""Tag entity_timeline job 构建。"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from core.modules.tag.engines.shared.global_cache import build_global_extra_cache
from core.modules.tag.engines.shared.helper.job_helper import JobHelper
from core.modules.tag.enums import TagTargetType, TagUpdateMode
from core.modules.tag.models.scenario_model import ScenarioModel

logger = logging.getLogger(__name__)


def resolve_worker_ref(scenario_cache: Dict[str, Any]) -> tuple[str, str, str]:
    if not scenario_cache:
        raise ValueError("Scenario 不在缓存中")
    worker_module_path = scenario_cache.get("worker_module_path")
    worker_class_name = scenario_cache.get("worker_class_name")
    worker_file_path = str(scenario_cache.get("worker_file_path") or "")
    if not worker_module_path or not worker_class_name:
        raise ValueError(
            f"缺少 worker 模块信息: worker_module_path={worker_module_path}, "
            f"worker_class_name={worker_class_name}"
        )
    return str(worker_module_path), str(worker_class_name), worker_file_path


def build_timeline_jobs(
    *,
    entity_list: List[str],
    settings: Dict[str, Any],
    scenario_model: ScenarioModel,
    scenario_cache: Dict[str, Any],
    tag_data_service: Any,
    dcm: Any,
    log_job_grouping: bool = True,
) -> List[Dict[str, Any]]:
    update_mode = scenario_model.calculate_update_mode()
    scenario_name = scenario_model.get_name()
    default_start_date = settings.get("start_date")
    default_end_date = settings.get("end_date")

    tag_target_type = str(
        settings.get("tag_target_type") or TagTargetType.ENTITY_BASED.value
    ).strip().lower()
    attach_to_data_key = scenario_model.attach_to_data_key  # 直接从 ScenarioModel 获取（DataKey）

    tag_models = scenario_model.get_tag_models()
    tag_definitions = [tag_model.to_dict() for tag_model in tag_models]

    entity_last_update_info: Dict[str, Any] = {}
    if update_mode == TagUpdateMode.INCREMENTAL and tag_data_service:
        entity_last_update_info = tag_data_service.get_tag_value_last_update_info(
            scenario_name
        )

    global_extra_cache = build_global_extra_cache(
        settings,
        dcm=dcm,
        start=default_start_date,
        end=default_end_date,
    )
    latest_completed = JobHelper._resolve_latest_completed_trading_date()
    worker_module_path, worker_class_name, worker_file_path = resolve_worker_ref(scenario_cache)

    entity_specs: List[Dict[str, Any]] = []
    for entity_id in entity_list:
        entity_last_update_date = None
        if update_mode == TagUpdateMode.INCREMENTAL:
            entity_info = entity_last_update_info.get(entity_id, {})
            entity_last_update_date = entity_info.get("max_as_of_date")

        start_date, end_date = JobHelper.calculate_start_and_end_date(
            update_mode=update_mode,
            entity_last_update_date=entity_last_update_date,
            default_start_date=default_start_date,
            default_end_date=default_end_date,
            latest_completed_trading_date=latest_completed,
        )
        entity_specs.append(
            {
                "entity_id": entity_id,
                "start_date": start_date,
                "end_date": end_date,
            }
        )

    shared_payload = {
        "attach_to_data_key": attach_to_data_key,  # DataKey（例如 "stock.kline.daily"）
        "scenario_name": scenario_name,
        "update_mode": update_mode,
        "tag_definitions": tag_definitions,
        "settings": settings,
        "worker_module_path": worker_module_path,
        "worker_class_name": worker_class_name,
        "worker_file_path": worker_file_path,
        "global_extra_cache": global_extra_cache,
    }
    scenario_id = scenario_model.get_identifier()
    jobs: List[Dict[str, Any]] = []
    for ent in entity_specs:
        job_id = f"{scenario_id}_{ent['entity_id']}"
        jobs.append(
            {
                "id": job_id,
                "payload": {**shared_payload, **ent, "_job_id": job_id},
            }
        )

    if log_job_grouping:
        logger.info(
            "Tag jobs 分组: entities=%d, dispatch_jobs=%d（batch 由 BacktestEngine 规划）",
            len(entity_specs),
            len(jobs),
        )
    return jobs
