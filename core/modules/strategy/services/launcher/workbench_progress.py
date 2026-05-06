"""V2-06：轮询单次 step 任务进度。"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .workbench_jobs import job_get, job_resolve_id


def _progress_payload(row: Dict[str, Any]) -> Dict[str, Any]:
    progress = round(float(row.get("progress") or 0), 2)
    status = str(row.get("status") or "unknown")
    out: Dict[str, Any] = {"progress": progress, "status": status}
    if status == "completed":
        out["is_success"] = True
        sid = int(row.get("snapshot_id") or 0)
        if sid > 0:
            out["snapshot_id"] = sid
            out["version_id"] = f"v{sid}"
    elif status == "failed":
        out["is_success"] = False
        err = row.get("error")
        if err:
            out["reason"] = str(err)
    else:
        out["is_success"] = None
    return out


def get_step_progress(
    *,
    strategy_name: str,
    normalized_step: str,
    job_id: str,
) -> Optional[Dict[str, Any]]:
    """
    返回契约进度体并附带 ``job_id``；``job_id`` 须与路径一致且任务存在，否则 ``None``。
    """
    jid = job_resolve_id(strategy_name, normalized_step, job_id)
    if not jid:
        return None
    row = job_get(jid)
    if not row:
        return None
    payload = _progress_payload(row)
    payload["job_id"] = jid
    return payload
