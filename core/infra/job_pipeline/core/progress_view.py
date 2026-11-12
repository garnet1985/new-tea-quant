"""把 ``infra.progress`` 节点快照压成任务表上的 progress 字段。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def _safe_id(raw: str) -> str:
    return (
        str(raw or "")
        .replace("/", "-")
        .replace("\\", "-")
        .replace("\x00", "")
        .strip()
    )


def progress_root_candidates(job: Dict[str, Any]) -> List[str]:
    """按 kind 推断 Progress 根 id（与业务侧命名对齐）。"""
    jid = str(job.get("job_id") or "").strip()
    if not jid:
        return []
    kind = str(job.get("kind") or "").strip()
    resource = str(job.get("resource_key") or "").strip()
    out: List[str] = []

    def add(value: str) -> None:
        text = _safe_id(value)
        if text and text not in out:
            out.append(text)

    if kind == "tag_run" and resource:
        add(f"tag-{resource}-{jid}")
    if kind in {
        "strategy_run",
        "strategy_scan",
        "strategy_attribute",
        "strategy_rolling",
    } and resource:
        add(f"pipeline-{resource}-{jid}")
    # data_renew 等直接用 job_id；兜底也试裸 id
    add(jid)
    return out


def read_progress_snapshot_for_job(job: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """按任务快照解析 Progress 根并压成摘要。"""
    try:
        from core.infra.progress import Progress
    except Exception:
        return None
    for root in progress_root_candidates(job):
        try:
            raw = Progress.read(root)
        except Exception:
            continue
        if not isinstance(raw, dict):
            continue
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
            "updated_at": raw.get("updated_at"),
            "started_at": raw.get("started_at"),
            "root_id": root,
        }
    return None


def attach_progress(job: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """给任务快照挂上 progress；已有非空 progress 则不覆盖。"""
    if not isinstance(job, dict):
        return job
    out = dict(job)
    existing = out.get("progress")
    if isinstance(existing, dict) and existing:
        return out
    snap = read_progress_snapshot_for_job(out)
    if snap is not None:
        out["progress"] = snap
    return out
