"""Strategy → BacktestEngine job wrapping (callers must supply canonical fields)."""
from __future__ import annotations

from typing import Any, Dict

from core.modules.backtest_engine.contracts import BacktestJob


def require_stock_id(job: Dict[str, Any], *, label: str = "stock job") -> str:
    stock_id = str(job.get("stock_id") or "").strip()
    if not stock_id:
        raise ValueError(f"{label} requires stock_id")
    return stock_id


def wrap_timeline_stock_job(job: Dict[str, Any], **payload_extra: Any) -> Dict[str, Any]:
    stock_id = require_stock_id(job, label="timeline stock job")
    payload = dict(job)
    payload.update(payload_extra)
    return BacktestJob(id=stock_id, payload=payload).to_dict()


def require_dispatch_job_id(job: Dict[str, Any], *, label: str = "dispatch job") -> str:
    job_id = str(job.get("job_id") or "").strip()
    if not job_id:
        raise ValueError(f"{label} requires job_id")
    return job_id


def wrap_slice_dispatch_job(job: Dict[str, Any], **payload_extra: Any) -> Dict[str, Any]:
    job_id = require_dispatch_job_id(job, label="calendar_slice dispatch job")
    payload = dict(job)
    payload.update(payload_extra)
    return BacktestJob(id=job_id, payload=payload).to_dict()


__all__ = [
    "require_dispatch_job_id",
    "require_stock_id",
    "wrap_slice_dispatch_job",
    "wrap_timeline_stock_job",
]
