"""Tag calendar_slice 执行流水线。"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from core.modules.market_profile.constants import DEFAULT_PROFILE_ID
from core.modules.strategy.engines.shared.helpers.backtest_calendar_context import (
    build_backtest_calendar_context,
)
from core.modules.strategy.engines.shared.helpers.backtest_date_resolve import (
    BacktestDateRange,
)
from core.modules.tag.engines.shared.global_cache import build_global_extra_cache
from core.modules.tag.engines.shared.runner import execute_tag_jobs
from core.modules.tag.engines.sliced.slice_job import build_tag_calendar_slice_job
from core.modules.tag.engines.timeline.job_builder import resolve_worker_ref
from core.modules.tag.engines.timeline.pipeline import profile_enabled_for
from core.modules.tag.models.scenario_model import ScenarioModel

logger = logging.getLogger(__name__)


def run_sliced_pipeline(
    mgr: Any,
    *,
    scenario_model: ScenarioModel,
    entity_list: List[str],
    settings: Dict[str, Any],
    tag_key: str,
) -> None:
    scenario_name = scenario_model.get_name()
    scenario_cache = mgr.scenario_cache.get(tag_key) or {}
    worker_module_path, worker_class_name, worker_file_path = resolve_worker_ref(scenario_cache)

    start_date = str(settings.get("start_date") or "")
    end_date = str(settings.get("end_date") or "")
    global_extra_cache = build_global_extra_cache(
        settings,
        dcm=mgr._data_contract_manager,
        start=start_date,
        end=end_date,
    )

    payload = build_tag_calendar_slice_job(
        entity_ids=entity_list,
        settings=settings,
        scenario_model=scenario_model,
        worker_module_path=worker_module_path,
        worker_class_name=worker_class_name,
        worker_file_path=worker_file_path,
        global_extra_cache=global_extra_cache,
    )
    calendar_ctx = build_backtest_calendar_context(
        data_manager=mgr.data_mgr,
        period=BacktestDateRange(start_date, end_date, "", ""),
        market_profile_id=DEFAULT_PROFILE_ID,
    )
    payload["backtest_calendar"] = calendar_ctx.to_dict()

    scenario_id = scenario_model.get_identifier()
    job_id = f"{scenario_id}_calendar_slice"
    jobs = [{"id": job_id, "payload": {**payload, "_job_id": job_id}}]

    performance = dict(settings.get("performance") or {})
    performance.update(mgr._dispatch_overrides)
    performance["max_workers"] = 1
    performance["stage_in_worker"] = False

    logger.info(
        "[%s] Tag calendar_slice: entities=%d, job=1",
        scenario_name,
        len(entity_list),
    )
    execute_tag_jobs(
        data_mgr=mgr.data_mgr,
        tag_data_service=mgr.tag_data_service,
        jobs=jobs,
        scenario_name=scenario_name,
        performance=performance,
        profile_enabled=profile_enabled_for(mgr, performance),
        on_tag_data_service_refresh=lambda svc: setattr(mgr, "tag_data_service", svc),
        on_pipeline_progress=getattr(mgr, "_pipeline_progress_callback", None),
    )
