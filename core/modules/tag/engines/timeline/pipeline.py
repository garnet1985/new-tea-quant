"""Tag entity_timeline 执行流水线。"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, TYPE_CHECKING, Type

from core.infra.job_pipeline import ExecuteMode
from core.infra.job_pipeline.profile import WorkerProfiles
from core.infra.worker.dispatch_planner import resolve_dispatch_plan
from core.modules.tag.engines.shared.backend import backend_is_duckdb, parse_execute_mode
from core.modules.tag.engines.shared.dispatch_probe import (
    DEFAULT_PROBE_ENTITIES,
    run_tag_dispatch_probe,
    should_run_dispatch_probe,
)
from core.modules.tag.engines.shared.runner import execute_tag_jobs
from core.modules.tag.engines.timeline.job_builder import build_timeline_jobs
from core.modules.tag.models.scenario_model import ScenarioModel

if TYPE_CHECKING:
    from core.modules.tag.engines.shared.base_worker import BaseTagWorker

logger = logging.getLogger(__name__)


def profile_enabled_for(mgr: Any, performance: Dict[str, Any]) -> bool:
    return bool(
        mgr.is_verbose
        or performance.get("profile")
        or os.environ.get("NTQ_TAG_PROFILE", "").strip() in ("1", "true", "yes")
    )


def run_timeline_pipeline(
    mgr: Any,
    *,
    scenario_model: ScenarioModel,
    entity_list: List[str],
    settings: Dict[str, Any],
    worker_class: "Type[BaseTagWorker]",
    tag_key: str,
) -> None:
    scenario_name = scenario_model.get_name()
    performance = dict(settings.get("performance") or {})
    performance.update(mgr._dispatch_overrides)

    execute_mode = parse_execute_mode(performance.get("execute_mode"))
    if execute_mode == ExecuteMode.ELASTIC:
        raise NotImplementedError("ExecuteMode.ELASTIC is not implemented yet")

    if mgr.is_verbose:
        logger.debug(
            "timeline pipeline: tag_key=%s scenario=%s entities=%d",
            tag_key,
            scenario_name,
            len(entity_list),
        )

    measured_mb: Optional[float] = None
    ep_explicit = performance.get("entities_per_job") not in (None, "", "auto")
    scenario_cache = mgr.scenario_cache.get(tag_key) or {}

    if should_run_dispatch_probe(
        performance,
        total_entities=len(entity_list),
        entities_per_job_explicit=ep_explicit,
    ):
        probe_n = max(
            1,
            min(
                int(performance.get("dispatch_probe_entities", DEFAULT_PROBE_ENTITIES)),
                len(entity_list),
            ),
        )
        probe_jobs = build_timeline_jobs(
            entity_list=entity_list,
            settings=settings,
            scenario_model=scenario_model,
            scenario_cache=scenario_cache,
            tag_data_service=mgr.tag_data_service,
            dcm=mgr._data_contract_manager,
            entities_per_job=probe_n,
            log_job_grouping=False,
        )
        if probe_jobs and probe_jobs[0].get("payload"):
            logger.info(
                "[%s] Tag 调度探针: 子进程试跑 %d 股（与生产相同 stage+算）…",
                scenario_name,
                probe_n,
            )
            payload = dict(probe_jobs[0]["payload"])
            payload["_run_name"] = f"tag:{scenario_name}"
            try:
                from core.infra.db.engines.duckdb.process_pool_scope import (
                    duckdb_worker_pool_main_process,
                )

                with duckdb_worker_pool_main_process(
                    mgr.data_mgr,
                    resume_main_after=False,
                    wait_children_timeout_sec=15.0,
                ):
                    probe_result = run_tag_dispatch_probe(payload, performance=performance)
                    measured_mb = probe_result.mb_per_entity
            except Exception as exc:
                logger.warning("Tag 调度探针失败，回退默认 mb 估算: %s", exc)

    if backend_is_duckdb(mgr.data_mgr) and getattr(mgr.data_mgr, "db", None) is None:
        from core.infra.db.engines.duckdb.process_pool_scope import (
            resume_main_database_with_retry,
        )

        resume_main_database_with_retry(mgr.data_mgr)
        mgr.tag_data_service = mgr.data_mgr.stock.tags

    dispatch_plan = resolve_dispatch_plan(
        total_entities=len(entity_list),
        performance=performance,
        log_label="Tag",
        measured_mb_per_entity=measured_mb,
        worker_profile=WorkerProfiles.TAG,
    )
    performance["max_workers"] = dispatch_plan.max_workers
    performance["prefetch_ahead"] = dispatch_plan.prefetch_ahead

    jobs = build_timeline_jobs(
        entity_list=entity_list,
        settings=settings,
        scenario_model=scenario_model,
        scenario_cache=scenario_cache,
        tag_data_service=mgr.tag_data_service,
        dcm=mgr._data_contract_manager,
        entities_per_job=dispatch_plan.entities_per_job,
    )
    if not jobs:
        logger.warning("没有新的计算任务，跳过执行: scenario=%s", scenario_name)
        return

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
