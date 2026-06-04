"""策略机会枚举：调度规划（探针优先）。"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.infra.job_pipeline.worker_profile import WorkerProfiles
from core.infra.worker.dispatch_planner import DispatchPlan, resolve_dispatch_plan
from core.infra.worker.dispatch_probe import should_run_dispatch_probe
from core.modules.strategy.engines.simulator.enumerator.data_classes.settings import (
    OpportunityEnumeratorSettings,
)
from core.modules.strategy.services.execution.enum_dispatch_probe import (
    default_probe_entity_count,
    run_enum_dispatch_probe,
)

LOG_LABEL = "策略枚举"


def enumerator_performance_dict(
    enum_settings: OpportunityEnumeratorSettings,
) -> Dict[str, Any]:
    """将 enumerator 配置转为 dispatch_planner 可读形态。"""
    raw = dict(enum_settings.raw.get("enumerator") or {})
    perf: Dict[str, Any] = {
        "memory_budget_mb": raw.get("memory_budget_mb", "auto"),
        "memory_floor_mb": raw.get("memory_floor_mb", "auto"),
        "entities_per_job": raw.get("entities_per_job", "auto"),
        "dispatch_probe": raw.get("dispatch_probe", True),
    }
    for key in (
        "entities_per_job_min",
        "entities_per_job_max",
        "mb_per_entity_staged",
        "worker_memory_fraction",
        "dispatch_probe_entities",
        "dispatch_probe_safety_factor",
        "main_process_reserve_mb",
    ):
        if raw.get(key) not in (None, ""):
            perf[key] = raw[key]
    return perf


def entities_per_job_is_explicit(performance: Dict[str, Any]) -> bool:
    return performance.get("entities_per_job") not in (None, "", "auto")


def resolve_entities_per_job(
    *,
    total_stocks: int,
    enum_settings: OpportunityEnumeratorSettings,
    measured_mb_per_entity: Optional[float] = None,
) -> int:
    perf = enumerator_performance_dict(enum_settings)
    if entities_per_job_is_explicit(perf):
        return max(1, int(perf["entities_per_job"]))
    return resolve_enum_dispatch_plan(
        total_stocks=total_stocks,
        enum_settings=enum_settings,
        measured_mb_per_entity=measured_mb_per_entity,
    ).entities_per_job


def resolve_enum_dispatch_plan(
    *,
    total_stocks: int,
    enum_settings: OpportunityEnumeratorSettings,
    measured_mb_per_entity: Optional[float] = None,
) -> DispatchPlan:
    return resolve_dispatch_plan(
        total_entities=total_stocks,
        performance=enumerator_performance_dict(enum_settings),
        log_label=LOG_LABEL,
        measured_mb_per_entity=measured_mb_per_entity,
        worker_profile=WorkerProfiles.ENUMERATOR,
    )


def maybe_run_enum_dispatch_probe(
    *,
    strategy_name: str,
    stock_ids: List[str],
    settings_payload: Dict[str, Any],
    output_dir: str,
    worker_ref: Dict[str, str],
    start_date: str,
    end_date: str,
    enum_settings: OpportunityEnumeratorSettings,
    global_extra_cache: Dict[str, Any],
    market_profile_id: str,
    backtest_calendar: Dict[str, Any],
    data_mgr: Any,
) -> Optional[float]:
    """
    auto 且未手写 mb_per_entity_staged 时试跑 1 个 bulk job，返回 measured_mb_per_entity。
    """
    perf = enumerator_performance_dict(enum_settings)
    if not should_run_dispatch_probe(
        perf,
        total_entities=len(stock_ids),
        entities_per_job_explicit=entities_per_job_is_explicit(perf),
    ):
        return None

    from core.infra.db.engines.duckdb.process_pool_scope import (
        duckdb_worker_pool_main_process,
    )
    from core.modules.strategy.engines.simulator.enumerator.dispatch_jobs import (
        build_dispatch_jobs,
    )

    probe_n = default_probe_entity_count(
        perf,
        total_stocks=len(stock_ids),
        entities_per_job_min=int(perf.get("entities_per_job_min", 1)),
    )
    probe_jobs = build_dispatch_jobs(
        strategy_name=strategy_name,
        settings_payload=settings_payload,
        output_dir=output_dir,
        worker_ref=worker_ref,
        stock_ids=stock_ids[:probe_n],
        start_date=start_date,
        end_date=end_date,
        entities_per_job=probe_n,
    )
    if not probe_jobs:
        return None

    from core.modules.strategy.services.execution.enum_job_pipeline import (
        build_enumeration_payload,
    )

    payload = build_enumeration_payload(probe_jobs[0], global_extra_cache)
    payload["market_profile_id"] = market_profile_id
    payload["backtest_calendar"] = backtest_calendar
    payload["_run_name"] = f"enum:{strategy_name}:probe"

    with duckdb_worker_pool_main_process(
        data_mgr,
        resume_main_after=False,
        wait_children_timeout_sec=15.0,
    ):
        result = run_enum_dispatch_probe(payload, performance=perf)
    return result.mb_per_entity
