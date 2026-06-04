"""价格因子：时间调度探针（C=秒/股，O=秒/job）。"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from core.infra.worker.dispatch_probe import (
    DEFAULT_PROBE_ENTITIES,
    PROBE_EXECUTOR_STRATEGY_PRICE,
    run_dispatch_probe_in_subprocess,
)


@dataclass(frozen=True)
class PriceDispatchTiming:
    entities_sampled: int
    sec_per_entity: float
    sec_per_job_overhead: float
    wall_inprocess_sec: float
    wall_subprocess_sec: float


def default_probe_entity_count(
    performance: Dict[str, Any],
    *,
    total_stocks: int,
) -> int:
    raw = performance.get("dispatch_probe_entities", DEFAULT_PROBE_ENTITIES)
    try:
        n = int(raw)
    except (TypeError, ValueError):
        n = DEFAULT_PROBE_ENTITIES
    return max(1, min(n, total_stocks))


def _run_inprocess_batch(stock_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    from core.modules.strategy.engines.simulator.price_factor.worker import (
        run_price_factor_payload,
    )

    payload = {
        "job_id": "price_probe_inprocess",
        "stock_jobs": list(stock_jobs),
        "strategy_name": stock_jobs[0].get("strategy_name"),
        "output_version_dir": stock_jobs[0].get("output_version_dir"),
        "config": stock_jobs[0].get("config"),
        "market_profile_id": stock_jobs[0].get("market_profile_id"),
        "backtest_calendar": stock_jobs[0].get("backtest_calendar"),
        "_dispatch_probe": True,
        "_bench_skip_save": True,
    }
    result = run_price_factor_payload(payload, in_subprocess=False)
    rows = result.get("stock_results") if isinstance(result, dict) else None
    return list(rows) if isinstance(rows, list) else []


def execute_price_probe_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """子进程探针：与 ``execute_price_factor_job`` 相同 batch 路径。"""
    from core.infra.job_pipeline.types import JobContext
    from core.modules.strategy.services.execution.price_job_pipeline import (
        execute_price_factor_job,
    )

    ctx = JobContext(
        job_id=str(payload.get("job_id") or "price_probe"),
        payload=dict(payload),
        run_name=str(payload.get("_run_name") or "price:probe"),
    )
    return execute_price_factor_job(ctx)


def run_price_dispatch_timing_probe(
    *,
    per_stock_jobs: List[Dict[str, Any]],
    performance: Optional[Dict[str, Any]] = None,
) -> PriceDispatchTiming:
    """
    主进程跑 K 股 → C；子进程跑同 K 股 batch job → O ≈ wall_sub - wall_in。
    """
    performance = dict(performance or {})
    probe_n = default_probe_entity_count(performance, total_stocks=len(per_stock_jobs))
    sample = [dict(j) for j in per_stock_jobs[:probe_n]]
    for row in sample:
        row["_bench_skip_save"] = True
        row["_dispatch_probe"] = True

    k = len(sample)
    if k < 1:
        return PriceDispatchTiming(
            entities_sampled=0,
            sec_per_entity=0.001,
            sec_per_job_overhead=0.15,
            wall_inprocess_sec=0.0,
            wall_subprocess_sec=0.0,
        )

    t0 = time.perf_counter()
    _run_inprocess_batch(sample)
    wall_in = time.perf_counter() - t0

    from core.modules.strategy.services.execution.price_dispatch import (
        release_main_duckdb_handles,
    )

    release_main_duckdb_handles()

    batch_payload: Dict[str, Any] = {
        "job_id": "price_probe_subprocess",
        "stock_jobs": sample,
        "strategy_name": sample[0].get("strategy_name"),
        "output_version_dir": sample[0].get("output_version_dir"),
        "config": sample[0].get("config"),
        "market_profile_id": sample[0].get("market_profile_id"),
        "backtest_calendar": sample[0].get("backtest_calendar"),
        "_dispatch_probe": True,
        "_bench_skip_save": True,
        "_probe_entity_count": k,
        "_run_name": "price:probe",
    }
    probe_raw = run_dispatch_probe_in_subprocess(
        batch_payload,
        executor=PROBE_EXECUTOR_STRATEGY_PRICE,
        performance=performance,
        log_label="价格因子",
    )
    wall_sub = float(probe_raw.wall_sec)

    sec_per_entity = max(wall_in / k, 1e-6)
    sec_per_job_overhead = max(wall_sub - wall_in, 0.0)
    safety = max(1.0, float(performance.get("dispatch_probe_safety_factor", 1.1)))
    return PriceDispatchTiming(
        entities_sampled=k,
        sec_per_entity=sec_per_entity * safety,
        sec_per_job_overhead=sec_per_job_overhead * safety,
        wall_inprocess_sec=wall_in,
        wall_subprocess_sec=wall_sub,
    )


__all__ = [
    "PriceDispatchTiming",
    "default_probe_entity_count",
    "execute_price_probe_payload",
    "run_price_dispatch_timing_probe",
]
