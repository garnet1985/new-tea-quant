"""Workbench 异步 step 任务状态（进程内单例；供 run / progress / report 共用）。"""

from __future__ import annotations

import threading
import uuid
from typing import Any, Dict, Optional

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


def job_resolve_id(
    strategy_name: str,
    normalized_step: str,
    job_id: str,
) -> Optional[str]:
    """
    校验 ``job_id`` 对应任务存在且与路径上的 ``strategy_name`` / ``step`` 一致。
    """
    jid = str(job_id or "").strip()
    if not jid:
        return None
    name = str(strategy_name).strip()
    step_key = str(normalized_step).strip()
    row = job_get(jid)
    if not row:
        return None
    if row.get("strategy_name") != name or row.get("step") != step_key:
        return None
    return jid


def job_update(job_id: str, **fields: Any) -> None:
    with _LOCK:
        row = _JOBS.get(job_id)
        if row is None:
            return
        row.update(fields)


def job_get(job_id: str) -> Optional[Dict[str, Any]]:
    with _LOCK:
        row = _JOBS.get(job_id)
        return dict(row) if row else None
