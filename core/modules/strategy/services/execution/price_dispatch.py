"""价格因子：dispatch 规划（entities_per_job 为主旋钮）。"""
from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional

from core.infra.job_pipeline.worker_profile import (
    WorkerProfiles,
    resolve_pipeline_workers,
)
from core.infra.worker.dispatch_time_planner import (
    TimeDispatchPlan,
    resolve_time_dispatch_plan,
)
from core.modules.strategy.engines.simulator.price_factor.data_classes.settings import (
    DEFAULT_PRICE_ENTITIES_PER_JOB,
    StrategyPriceSimulatorSettings,
)
from core.modules.strategy.services.execution.price_dispatch_probe import (
    run_price_dispatch_timing_probe,
)

LOG_LABEL = "价格因子"
logger = logging.getLogger(__name__)


def release_main_duckdb_handles(data_mgr: Any = None) -> None:
    """主进程释放 DuckDB 文件锁，便于子进程 probe / ProcessPool。"""
    from core.infra.db.engines.duckdb.process_pool_scope import (
        release_all_main_db_handles,
        wait_pool_children_done,
    )
    from core.modules.data_manager import DataManager

    dm = data_mgr
    if dm is None:
        dm = DataManager.get_instance()
    if dm is not None:
        release_all_main_db_handles(dm)
    DataManager.reset_instance()
    wait_pool_children_done(timeout_sec=15.0)


def price_performance_dict(config: StrategyPriceSimulatorSettings) -> Dict[str, Any]:
    raw = dict(config.price_simulator)
    perf: Dict[str, Any] = {
        "entities_per_job": raw.get("entities_per_job", DEFAULT_PRICE_ENTITIES_PER_JOB),
        "dispatch_probe": raw.get("dispatch_probe", False),
    }
    for key in (
        "dispatch_probe_entities",
        "dispatch_probe_safety_factor",
        "sec_per_entity_staged",
        "sec_per_job_overhead_staged",
        "force_main_process",
    ):
        if raw.get(key) not in (None, ""):
            perf[key] = raw[key]
    return perf


def entities_per_job_is_explicit(performance: Dict[str, Any]) -> bool:
    return performance.get("entities_per_job") not in (None, "", "auto")


def should_run_price_dispatch_probe(
    performance: Dict[str, Any],
    *,
    total_stocks: int,
) -> bool:
    if performance.get("dispatch_probe") is False:
        return False
    if entities_per_job_is_explicit(performance):
        return False
    if performance.get("sec_per_entity_staged") not in (None, ""):
        return False
    if total_stocks < 1:
        return False
    return True


def resolve_price_timing_metrics(
    *,
    performance: Dict[str, Any],
    measured: Optional[Any] = None,
) -> tuple[float, float]:
    staged_c = performance.get("sec_per_entity_staged")
    staged_o = performance.get("sec_per_job_overhead_staged")
    if staged_c not in (None, "") and staged_o not in (None, ""):
        return max(float(staged_c), 1e-6), max(float(staged_o), 0.0)
    if measured is not None:
        return max(float(measured.sec_per_entity), 1e-6), max(
            float(measured.sec_per_job_overhead), 0.0
        )
    raise ValueError(
        f"{LOG_LABEL}: entities_per_job=auto 需要 dispatch_probe 或 "
        "settings 中的 sec_per_entity_staged / sec_per_job_overhead_staged"
    )


def _resolve_explicit_entities_plan(
    *,
    total_stocks: int,
    performance: Dict[str, Any],
) -> TimeDispatchPlan:
    entities_per_job = max(1, int(performance["entities_per_job"]))
    dispatch_jobs = max(1, math.ceil(total_stocks / entities_per_job)) if total_stocks else 0
    max_workers = resolve_pipeline_workers(
        worker_id=WorkerProfiles.PRICE_FACTOR,
        dispatch_jobs=dispatch_jobs,
    )
    run_in_main = bool(performance.get("force_main_process", False))
    plan = TimeDispatchPlan(
        entities_per_job=entities_per_job,
        max_workers=max_workers,
        dispatch_jobs=dispatch_jobs,
        run_in_main_process=run_in_main,
        sec_per_entity=0.0,
        sec_per_job_overhead=0.0,
        estimated_wall_sec=0.0,
        source_entities_per_job="settings",
        source_max_workers="profile_auto",
    )
    logger.info(
        "%s 调度: entities=%s, entities_per_job=%s, jobs=%s, pool_workers=%s",
        LOG_LABEL,
        total_stocks,
        plan.entities_per_job,
        plan.dispatch_jobs,
        plan.max_workers,
    )
    return plan


def resolve_price_dispatch_plan(
    *,
    total_stocks: int,
    config: StrategyPriceSimulatorSettings,
    measured_timing: Optional[Any] = None,
) -> TimeDispatchPlan:
    perf = price_performance_dict(config)
    if entities_per_job_is_explicit(perf):
        return _resolve_explicit_entities_plan(
            total_stocks=total_stocks,
            performance=perf,
        )

    sec_c, sec_o = resolve_price_timing_metrics(
        performance=perf,
        measured=measured_timing,
    )
    return resolve_time_dispatch_plan(
        total_entities=total_stocks,
        performance=perf,
        sec_per_entity=sec_c,
        sec_per_job_overhead=sec_o,
        log_label=LOG_LABEL,
        worker_profile=WorkerProfiles.PRICE_FACTOR,
    )


def maybe_run_price_dispatch_probe(
    *,
    per_stock_jobs: List[Dict[str, Any]],
    config: StrategyPriceSimulatorSettings,
    data_mgr: Any,
) -> Optional[Any]:
    perf = price_performance_dict(config)
    if not should_run_price_dispatch_probe(perf, total_stocks=len(per_stock_jobs)):
        return None

    release_main_duckdb_handles(data_mgr)
    return run_price_dispatch_timing_probe(
        per_stock_jobs=per_stock_jobs,
        performance=perf,
    )


__all__ = [
    "LOG_LABEL",
    "maybe_run_price_dispatch_probe",
    "price_performance_dict",
    "release_main_duckdb_handles",
    "resolve_price_dispatch_plan",
    "should_run_price_dispatch_probe",
]
