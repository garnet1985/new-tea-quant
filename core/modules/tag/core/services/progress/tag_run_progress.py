"""Tag async run progress — disk via ProgressRecorder (tag-run channel)."""

from __future__ import annotations

from typing import Any, Dict, Optional

from core.modules.strategy.contracts import ProgressRecorder


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
                "label": "准备中…",
            }
        )
        self._publish(0, 0)

    def write(self, payload: Dict[str, Any]) -> None:
        base = {
            "tag_key": self.tag_key,
            "run_id": self.job_id,
            "job_id": self.job_id,
        }
        base.update(payload)
        self._recorder().record(base)

    def mark_running(self, *, label: str = "加载场景…") -> None:
        self.write(
            {
                "phase": "running",
                "status": "running",
                "label": label,
            }
        )

    def tick_from_pipeline(self, snapshot: Dict[str, Any]) -> None:
        finished = int(snapshot.get("finished") or snapshot.get("index") or 0)
        total = int(snapshot.get("total_jobs") or snapshot.get("total") or 0)
        label = f"执行计算 {finished}/{total}" if total else "执行计算…"
        self.write(
            {
                "phase": "running",
                "status": "running",
                "label": label,
            }
        )
        if total > 0 or finished > 0:
            self._publish(finished, total, detail=label)

    def complete(self) -> None:
        self.write(
            {
                "phase": "completed",
                "status": "completed",
                "label": "完成",
                "is_success": True,
            }
        )
        self._finish_shared()

    def _ensure_shared(self) -> str:
        from core.infra.progress import Progress

        root = _root_id(self.tag_key, self.job_id)
        existing = Progress.read(root)
        if (
            existing is None
            or str(existing.get("status") or "") in _TERMINAL
            or str(existing.get("job") or "") != "tag"
        ):
            Progress.start(root, job="tag", label="标签计算")
        return root

    def _publish(self, done: int, total: int, *, detail: str = "") -> None:
        from core.infra.progress import Progress

        root = self._ensure_shared()
        source = self.tag_key or self.job_id
        text = str(detail or "").strip()
        if total > 0:
            Progress.tick(
                root,
                min(done, total),
                total,
                source=source,
                detail=text or None,
                log=False,
            )
            return
        Progress.tick(root, 0, 1, source=source, detail=text or None, log=False)

    def _finish_shared(self) -> None:
        from core.infra.progress import Progress

        Progress.finish(self._ensure_shared())

    def _fail_shared(self, detail: str) -> None:
        from core.infra.progress import Progress

        root = _root_id(self.tag_key, self.job_id)
        if Progress.read(root) is None:
            return
        message = str(detail or "").splitlines()[0] if str(detail or "") else ""
        Progress.fail(root, detail=message)

    def fail(self, error: str) -> None:
        self.write(
            {
                "phase": "failed",
                "status": "failed",
                "error": str(error),
                "is_success": False,
            }
        )
        self._fail_shared(str(error))

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
            pct = _shared_percent(key, jid)
        except (TypeError, ValueError):
            pct = None
        if pct is None:
            pct = 100.0 if status == "completed" or phase == "completed" else 0.0
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

_TERMINAL = frozenset({"completed", "failed", "cancelled"})


def _root_id(tag_key: str, job_id: str) -> str:
    raw = f"tag-{tag_key}-{job_id}"
    safe = raw.replace("/", "-").replace("\\", "-").replace("\x00", "").strip()
    return safe or "tag"


def _shared_percent(tag_key: str, job_id: str) -> Optional[float]:
    from core.infra.progress import Progress

    snap = Progress.read(_root_id(tag_key, job_id))
    if not isinstance(snap, dict) or str(snap.get("job") or "") != "tag":
        return None
    source = str(tag_key or "").strip()
    if source and str(snap.get("source") or "") not in ("", source):
        return None
    return round(float(snap.get("ratio") or 0) * 100, 2)
