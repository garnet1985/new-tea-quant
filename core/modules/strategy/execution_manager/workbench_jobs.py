"""工作台异步 run 的进程内 job 表（BFF POST 立即返回 ``job_id``，轮询读磁盘进度）。"""

from __future__ import annotations

import threading
import uuid
from typing import Any, Dict

_LOCK = threading.Lock()
_JOBS: Dict[str, Dict[str, Any]] = {}


def job_create(*, strategy_name: str, step: str, is_force: bool) -> str:
    jid = str(uuid.uuid4())
    name = str(strategy_name).strip()
    st = str(step).strip()
    with _LOCK:
        _JOBS[jid] = {
            "strategy_name": name,
            "step": st,
            "is_force": bool(is_force),
            "progress": 0.0,
            "status": "queued",
            "error": None,
            "snapshot_id": 0,
        }
    return jid


def job_update(job_id: str, **fields: Any) -> None:
    with _LOCK:
        row = _JOBS.get(job_id)
        if row is None:
            return
        row.update(fields)


__all__ = ["job_create", "job_update"]
