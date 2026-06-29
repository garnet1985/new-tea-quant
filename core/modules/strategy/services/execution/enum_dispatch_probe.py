"""策略机会枚举：BacktestEngine timeline 探针执行入口。"""
from __future__ import annotations

from typing import Any, Dict

from core.modules.backtest_engine.core.shared.types import JobContext
from core.modules.strategy.services.execution.enum_job_pipeline import (
    execute_enumeration_timeline_job,
)
from core.modules.strategy.services.execution.worker_runtime import (
    bootstrap_strategy_worker_data_manager,
    release_strategy_worker_runtime,
)


def execute_enum_probe_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """子进程内执行（与 timeline batch job 相同路径）。"""
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


__all__ = ["execute_enum_probe_payload"]
