"""把 ``infra.progress`` 节点快照压成任务表上的 progress 字段。"""

from __future__ import annotations

from typing import Any, Dict, Optional


def read_progress_snapshot(job_id: str) -> Optional[Dict[str, Any]]:
    """按 job_id 读进度树根；没有则 ``None``。"""
    needle = str(job_id or "").strip()
    if not needle:
        return None
    try:
        from core.infra.progress import Progress

        raw = Progress.read(needle)
    except Exception:
        return None
    if not isinstance(raw, dict):
        return None
    try:
        ratio = float(raw.get("ratio") or 0.0)
    except (TypeError, ValueError):
        ratio = 0.0
    status = str(raw.get("status") or "").strip().lower()
    label = str(raw.get("label") or "").strip()
    detail = str(raw.get("detail") or "").strip()
    return {
        "ratio": max(0.0, min(1.0, ratio)),
        "percent": int(round(max(0.0, min(1.0, ratio)) * 100)),
        "status": status or None,
        "label": label or None,
        "detail": detail or None,
    }


def attach_progress(job: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """给任务快照挂上 progress；已有非空 progress 则不覆盖。"""
    if not isinstance(job, dict):
        return job
    out = dict(job)
    existing = out.get("progress")
    if isinstance(existing, dict) and existing:
        return out
    snap = read_progress_snapshot(str(out.get("job_id") or ""))
    if snap is not None:
        out["progress"] = snap
    return out
