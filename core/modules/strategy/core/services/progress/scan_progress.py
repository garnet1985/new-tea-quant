"""Scanner async job progress — disk via ProgressRecorder (strategy-scan channel).

不读 scan 落盘：opportunities 由 ``Strategy.scan_run`` 传入。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .progress_recorder import ProgressRecorder


class ScanProgress:
    """Seed / tick / terminal writes for strategy scanner runs."""

    def __init__(self, strategy_key: str, job_id: str) -> None:
        self.strategy_key = str(strategy_key or "").strip()
        self.job_id = str(job_id or "").strip()

    @classmethod
    def for_job(cls, strategy_key: str, job_id: str) -> "ScanProgress":
        return cls(strategy_key, job_id)

    def _recorder(self) -> ProgressRecorder:
        return ProgressRecorder.for_scanner_run(self.strategy_key, self.job_id)

    def _load(self) -> Dict[str, Any]:
        prev = self._recorder().get_progress()
        return dict(prev) if isinstance(prev, dict) else {}

    def seed(self, *, demo: bool, force: bool) -> None:
        self._recorder().record(
            {
                "strategy_name": self.strategy_key,
                "run_id": self.job_id,
                "phase": "queued",
                "status": "queued",
                "progress_pct": 0,
                "demo": bool(demo),
                "force": bool(force),
            }
        )
        self._publish(0, 0)

    def mark_running(self) -> None:
        base = self._load()
        base.update(
            {
                "strategy_name": self.strategy_key,
                "run_id": self.job_id,
                "phase": "running",
                "status": "running",
                "progress_pct": max(int(base.get("progress_pct") or 0), 1),
            }
        )
        self._recorder().record(base)

    def tick(self, payload: Dict[str, Any]) -> None:
        """ScannerPipeline ``on_progress`` payload → disk."""
        try:
            pct = float(payload.get("progress_pct", 0) or 0)
        except (TypeError, ValueError):
            pct = 0.0
        pct = max(0.0, min(99.9, pct))

        total_jobs = int(payload.get("total_jobs", 0) or 0)
        done_jobs = (
            int(payload.get("completed_jobs", 0) or 0)
            + int(payload.get("failed_jobs", 0) or 0)
            + int(payload.get("cancelled_jobs", 0) or 0)
        )

        base = self._load()
        base.update(
            {
                "strategy_name": self.strategy_key,
                "run_id": self.job_id,
                "phase": "running",
                "status": "running",
                "progress_pct": round(pct, 2),
                "total_jobs": total_jobs,
                "done_jobs": done_jobs,
                "last_job_id": str(payload.get("last_job_id") or ""),
                "last_job_status": str(payload.get("last_job_status") or ""),
            }
        )
        self._recorder().record(base)
        self._publish(done_jobs, total_jobs)

    def fail(self, error: str) -> None:
        base = self._load()
        base.update(
            {
                "strategy_name": self.strategy_key,
                "run_id": self.job_id,
                "phase": "failed",
                "status": "failed",
                "progress_pct": 100,
                "error": str(error),
            }
        )
        self._recorder().record(base)
        self._fail_shared(str(error))

    @staticmethod
    def opportunity_rows(opportunities: List[Any]) -> List[Dict[str, Any]]:
        return [
            {
                "stock_id": opp.stock_id,
                "stock_name": opp.stock_name,
                "trigger_date": opp.trigger_date,
                "trigger_price": opp.trigger_price,
                "signal_snapshot": opp.signal_snapshot or {},
            }
            for opp in opportunities
        ]

    def complete(
        self,
        report: Dict[str, Any],
        *,
        opportunities: Optional[List[Any]] = None,
    ) -> None:
        base = self._load()
        packed_report = dict(report or {})
        if opportunities is not None:
            packed_report["opportunities"] = self.opportunity_rows(opportunities)
        base.update(
            {
                "strategy_name": self.strategy_key,
                "run_id": self.job_id,
                "phase": "completed",
                "status": "completed",
                "progress_pct": 100,
                "report": packed_report,
            }
        )
        base.pop("error", None)
        self._recorder().record(base)
        self._finish_shared()

    def _ensure_shared(self):
        from core.infra.progress import Progress

        root = _root_id(self.strategy_key, self.job_id)
        existing = Progress.read(root)
        if (
            existing is None
            or str(existing.get("status") or "") in _TERMINAL
            or str(existing.get("job") or "") != "scan"
        ):
            Progress.start(root, job="scan", label="扫描")
        return root

    def _publish(self, done: int, total: int) -> None:
        from core.infra.progress import Progress

        root = self._ensure_shared()
        source = self.strategy_key or self.job_id
        if total > 0:
            Progress.tick(root, min(done, total), total, source=source, log=False)
            return
        Progress.tick(root, 0, 1, source=source, log=False)

    def _finish_shared(self) -> None:
        from core.infra.progress import Progress

        Progress.finish(self._ensure_shared())

    def _fail_shared(self, detail: str) -> None:
        from core.infra.progress import Progress

        root = _root_id(self.strategy_key, self.job_id)
        if Progress.read(root) is None:
            return
        message = str(detail or "").splitlines()[0] if str(detail or "") else ""
        Progress.fail(root, detail=message)

    @classmethod
    def get_raw(cls, strategy_key: str, job_id: str) -> Optional[Dict[str, Any]]:
        sn = str(strategy_key or "").strip()
        jid = str(job_id or "").strip()
        if not jid:
            return None
        disk = ProgressRecorder.for_scanner_run(sn, jid).get_progress()
        if not isinstance(disk, dict) or not disk:
            return None
        stored = str(disk.get("strategy_name") or "").strip()
        if stored and sn and stored != sn:
            return None
        return disk

    @classmethod
    def get_poll_dto(
        cls, strategy_key: str, job_id: str
    ) -> Optional[Dict[str, Any]]:
        """Shape expected by BFF scan progress polling."""
        jid = str(job_id or "").strip()
        disk = cls.get_raw(strategy_key, jid)
        if not disk:
            return None

        status = str(disk.get("status") or "").strip().lower()
        phase = str(disk.get("phase") or "").strip().lower()
        err = disk.get("error")

        if status == "failed" or phase == "failed":
            out: Dict[str, Any] = {
                "progress": 100.0,
                "status": "failed",
                "job_id": jid,
                "is_success": False,
            }
            if err:
                out["reason"] = str(err)
            return out

        try:
            pct = _shared_percent(str(strategy_key or "").strip(), jid)
            if pct is None:
                pct = float(disk.get("progress_pct") or 0)
        except (TypeError, ValueError):
            pct = 0.0
        pct = max(0.0, min(100.0, pct))
        done = pct >= 100.0 or status == "completed" or phase == "completed"

        out = {
            "progress": round(pct, 2),
            "status": "completed" if done else "running",
            "job_id": jid,
        }
        if "demo" in disk:
            out["demo"] = bool(disk.get("demo"))
        if done:
            out["is_success"] = True
            report = disk.get("report")
            if isinstance(report, dict):
                out["report"] = report
        else:
            out["is_success"] = None
            for k in ("total_jobs", "done_jobs", "last_job_id", "last_job_status"):
                if k in disk:
                    out[k] = disk.get(k)
        return out


__all__ = ["ScanProgress"]

_TERMINAL = frozenset({"completed", "failed", "cancelled"})


def _root_id(strategy_key: str, job_id: str) -> str:
    raw = f"scan-{strategy_key}-{job_id}"
    safe = raw.replace("/", "-").replace("\\", "-").replace("\x00", "").strip()
    return safe or "scan"


def _shared_percent(strategy_key: str, job_id: str) -> Optional[float]:
    from core.infra.progress import Progress

    snap = Progress.read(_root_id(strategy_key, job_id))
    if not isinstance(snap, dict) or str(snap.get("job") or "") != "scan":
        return None
    source = str(strategy_key or "").strip()
    if source and str(snap.get("source") or "") not in ("", source):
        return None
    return round(float(snap.get("ratio") or 0) * 100, 2)
