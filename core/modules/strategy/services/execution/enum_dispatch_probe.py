"""策略机会枚举调度探针。"""
from __future__ import annotations

from typing import Any, Dict, Optional

from core.infra.worker.dispatch_probe import (
    DEFAULT_PROBE_ENTITIES,
    PROBE_EXECUTOR_STRATEGY_ENUM,
    DispatchProbeResult,
    run_dispatch_probe_in_subprocess,
)


def execute_enum_probe_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """子进程内执行（与 timeline batch job 相同路径）。"""
    from core.infra.job_pipeline.types import JobContext
    from core.modules.strategy.services.execution.enum_job_pipeline import (
        execute_enumeration_timeline_job,
    )
    from core.modules.strategy.services.execution.worker_runtime import (
        bootstrap_strategy_worker_data_manager,
        release_strategy_worker_runtime,
    )

    bootstrap_strategy_worker_data_manager()
    try:
        ctx = JobContext(
            job_id=str(payload.get("job_id") or "enum_probe"),
            payload=dict(payload),
            run_name=str(payload.get("_run_name") or "enum:probe"),
        )
        return execute_enumeration_timeline_job(ctx)
    finally:
        release_strategy_worker_runtime()


def run_enum_dispatch_probe(
    probe_job_payload: Dict[str, Any],
    *,
    performance: Optional[Dict[str, Any]] = None,
) -> DispatchProbeResult:
    payload = dict(probe_job_payload)
    stock_ids = payload.get("stock_ids") or []
    if isinstance(stock_ids, list):
        payload["_probe_entity_count"] = max(1, len(stock_ids))
    else:
        payload["_probe_entity_count"] = 1
    payload["_dispatch_probe"] = True
    payload.pop("output_dir", None)

    return run_dispatch_probe_in_subprocess(
        payload,
        executor=PROBE_EXECUTOR_STRATEGY_ENUM,
        performance=performance,
        log_label="策略枚举",
    )


def default_probe_entity_count(
    performance: Dict[str, Any],
    *,
    total_stocks: int,
    entities_per_job_min: int = 1,
) -> int:
    raw = performance.get("dispatch_probe_entities", DEFAULT_PROBE_ENTITIES)
    try:
        n = int(raw)
    except (TypeError, ValueError):
        n = DEFAULT_PROBE_ENTITIES
    return max(entities_per_job_min, min(n, total_stocks))
