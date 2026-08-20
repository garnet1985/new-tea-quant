"""Scanner async job progress — disk via ProgressRecorder (strategy-scan channel)."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from core.modules.strategy.core.engines.scanner.helpers import ScanCacheManager

from .progress_recorder import ProgressRecorder

logger = logging.getLogger(__name__)


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
        cache_key: str = "",
    ) -> None:
        base = self._load()
        packed_report = dict(report or {})
        try:
            scan_date = str(packed_report.get("date") or "").strip()
            disk_key = str(
                cache_key or packed_report.get("strategy_key") or self.strategy_key
            ).strip()
            if scan_date and disk_key:
                cache = ScanCacheManager(disk_key)
                opportunities = cache.load_opportunities(scan_date)
                packed_report["opportunities"] = self.opportunity_rows(opportunities)
        except Exception:
            logger.exception(
                "Failed to attach opportunities for job_id=%s strategy=%s",
                self.job_id,
                self.strategy_key,
            )
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
