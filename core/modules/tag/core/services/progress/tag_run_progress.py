"""Tag async run progress — disk via ProgressRecorder (tag-run channel)."""

from __future__ import annotations

from typing import Any, Dict, Optional

from core.modules.strategy.core.services.progress import ProgressRecorder


class TagRunProgress:
    """Seed / tick / terminal writes for tag UI runs."""

    def __init__(self, tag_key: str, job_id: str) -> None:
        self.tag_key = str(tag_key or "").strip()
        self.job_id = str(job_id or "").strip()

    @classmethod
    def for_job(cls, tag_key: str, job_id: str) -> "TagRunProgress":
        return cls(tag_key, job_id)

    def _recorder(self) -> ProgressRecorder:
        return ProgressRecorder.for_tag_run(self.tag_key, self.job_id)

    def seed(self) -> None:
        self._recorder().record(
            {
                "tag_key": self.tag_key,
                "run_id": self.job_id,
                "job_id": self.job_id,
                "phase": "queued",
                "status": "queued",
                "progress_pct": 0,
                "label": "准备中…",
            }
        )

    def write(self, payload: Dict[str, Any]) -> None:
        base = {
            "tag_key": self.tag_key,
            "run_id": self.job_id,
            "job_id": self.job_id,
        }
        base.update(payload)
        self._recorder().record(base)

    def mark_running(self, *, label: str = "加载场景…", progress_pct: float = 1) -> None:
        self.write(
            {
                "phase": "running",
                "status": "running",
                "progress_pct": progress_pct,
                "label": label,
            }
        )

    def tick_from_pipeline(self, snapshot: Dict[str, Any]) -> None:
        finished = int(snapshot.get("finished") or 0)
        total = int(snapshot.get("total_jobs") or 0)
        try:
            pct = float(snapshot.get("progress_pct") or 0)
        except (TypeError, ValueError):
            pct = 0.0
        pct = max(0.0, min(99.9, pct))
        label = f"执行计算 {finished}/{total}" if total else "执行计算…"
        self.write(
            {
                "phase": "running",
                "status": "running",
                "progress_pct": pct,
                "label": label,
            }
        )

    def complete(self) -> None:
        self.write(
            {
                "phase": "completed",
                "status": "completed",
                "progress_pct": 100,
                "label": "完成",
                "is_success": True,
            }
        )

    def fail(self, error: str) -> None:
        self.write(
            {
                "phase": "failed",
                "status": "failed",
                "progress_pct": 100,
                "error": str(error),
                "is_success": False,
            }
        )

    def on_progress_callback(self):
        def _cb(snapshot: Dict[str, Any]) -> None:
            self.tick_from_pipeline(snapshot)

        return _cb

    @classmethod
    def get_poll_dto(
        cls, *, tag_key: str, job_id: str
    ) -> Optional[Dict[str, Any]]:
        key = str(tag_key or "").strip()
        jid = str(job_id or "").strip()
        if not key or not jid:
            return None

        disk = ProgressRecorder.for_tag_run(key, jid).get_progress()
        if not isinstance(disk, dict) or not disk:
            return None
        if str(disk.get("tag_key") or "").strip() != key:
            return None

        status = str(disk.get("status") or "").strip().lower()
        phase = str(disk.get("phase") or status).strip().lower()
        err = disk.get("error")

        if status == "failed" or phase == "failed":
            out: Dict[str, Any] = {
                "progress": 100.0,
                "status": "failed",
                "phase": "failed",
                "job_id": jid,
                "run_id": jid,
                "tag_key": key,
                "is_success": False,
            }
            if err:
                out["reason"] = str(err)
            label = disk.get("label")
            if label:
                out["label"] = str(label)
            return out

        try:
            pct = float(disk.get("progress_pct") or 0)
        except (TypeError, ValueError):
            pct = 0.0
        pct = max(0.0, min(100.0, pct))
        done = pct >= 100.0 or status == "completed" or phase == "completed"

        out = {
            "progress": round(pct, 2),
            "status": "completed" if done else "running",
            "phase": "completed" if done else (phase or "running"),
            "job_id": jid,
            "run_id": jid,
            "tag_key": key,
        }
        label = disk.get("label")
        if label:
            out["label"] = str(label)
        if done:
            out["is_success"] = bool(disk.get("is_success", True))
        return out


__all__ = ["TagRunProgress"]
