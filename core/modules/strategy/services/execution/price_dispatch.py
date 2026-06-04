"""价格因子：时间探针 + dispatch 规划。"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.infra.worker.dispatch_time_planner import (
    TimeDispatchPlan,
    resolve_time_dispatch_plan,
)
from core.modules.strategy.engines.simulator.price_factor.data_classes.settings import (
    StrategyPriceSimulatorSettings,
)
from core.modules.strategy.services.execution.price_dispatch_probe import (
    run_price_dispatch_timing_probe,
)

LOG_LABEL = "价格因子"


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
        "max_workers": config.max_workers,
        "entities_per_job": raw.get("entities_per_job", "auto"),
        "reserve_cores": raw.get("reserve_cores", 1),
        "dispatch_probe": raw.get("dispatch_probe", True),
    }
    for key in (
        "max_workers_cap",
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


def resolve_price_dispatch_plan(
    *,
    total_stocks: int,
    config: StrategyPriceSimulatorSettings,
    measured_timing: Optional[Any] = None,
) -> TimeDispatchPlan:
    perf = price_performance_dict(config)
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
