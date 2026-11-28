"""running 槽存活与无进度写入 stale 判定。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from core.infra.job_pipeline.contracts import JobStatus
from core.infra.job_pipeline.core.pipeline_constants import (
    STALE_AFTER_NO_PROGRESS_SEC,
    STALE_AFTER_PROGRESS_SEC,
)


def _epoch_seconds(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value or "").strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        return datetime.fromisoformat(text).timestamp()
    except ValueError:
        return None


def progress_heartbeat_epoch(job: Dict[str, Any]) -> Optional[float]:
    """只认 Progress 写入时间（updated_at，其次 progress.started_at）。"""
    progress = job.get("progress") if isinstance(job.get("progress"), dict) else {}
    for key in ("updated_at", "started_at"):
        epoch = _epoch_seconds(progress.get(key))
        if epoch is not None:
            return epoch
    return None


def annotate_stale(
    job: Optional[Dict[str, Any]],
    *,
    now: Optional[float] = None,
    stale_after_progress_sec: int = STALE_AFTER_PROGRESS_SEC,
    stale_after_no_progress_sec: int = STALE_AFTER_NO_PROGRESS_SEC,
) -> Optional[Dict[str, Any]]:
    """进程仍在但进度长时间不写入 → ``status=stale``（不自动清槽）。

    - 有 Progress：看 ``updated_at``（默认 2h）
    - 无 Progress：才退回 running ``started_at``（默认 12h），避免重任务误伤
    """
    if not isinstance(job, dict):
        return job
    out = dict(job)
    status = str(out.get("status") or "").strip().lower()
    if status not in (JobStatus.RUNNING, JobStatus.STALE, ""):
        return out

    now_ts = float(now if now is not None else datetime.now(timezone.utc).timestamp())
    progress_beat = progress_heartbeat_epoch(out)
    if progress_beat is not None:
        age = now_ts - progress_beat
        limit = float(stale_after_progress_sec)
        source = "progress"
    else:
        started = _epoch_seconds(out.get("started_at"))
        if started is None:
            return out
        age = now_ts - started
        limit = float(stale_after_no_progress_sec)
        source = "started_at"

    if age < limit:
        out["stale"] = False
        return out
    out["status"] = JobStatus.STALE
    out["stale"] = True
    out["stale_age_sec"] = int(age)
    out["stale_source"] = source
    return out
