"""价格因子：BacktestEngine timeline 探针执行入口。"""
from __future__ import annotations

from typing import Any, Dict


def execute_price_probe_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """子进程探针：与 timeline batch job 相同路径。"""
    from core.modules.backtest_engine.core.shared.types import JobContext
    from core.modules.strategy.services.execution.price_job_pipeline import (
        execute_price_factor_timeline_job,
    )

    ctx = JobContext(
        job_id=str(payload.get("job_id") or "price_probe"),
        payload=dict(payload),
        run_name=str(payload.get("_run_name") or "price:probe"),
    )
    return execute_price_factor_timeline_job(ctx)


__all__ = ["execute_price_probe_payload"]
