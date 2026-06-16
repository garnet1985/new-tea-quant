#!/usr/bin/env python3
"""Calendar slice enumerator worker (Reader / Compute 双进程 v2)."""

from __future__ import annotations

from typing import Any, Dict
import logging

from core.modules.strategy.engines.simulator.enumerator.calendar_slice.runtime.orchestrator import (
    CalendarSliceProcessOrchestrator,
)

logger = logging.getLogger(__name__)


class CalendarSliceEnumeratorWorker:
    """Single job: orchestrator + Reader Lane + Compute Lane."""

    def __init__(self, job_payload: Dict[str, Any]):
        self.job_payload = job_payload
        self.stock_ids = [
            str(s).strip() for s in (job_payload.get("stock_ids") or []) if str(s).strip()
        ]
        if not self.stock_ids:
            raise ValueError("CalendarSliceEnumeratorWorker 缺少 stock_ids")

    def run(self) -> Dict[str, Any]:
        try:
            return CalendarSliceProcessOrchestrator(self.job_payload).run()
        except Exception as exc:
            logger.error("calendar_slice enumeration failed: %s", exc, exc_info=True)
            return {
                "success": False,
                "bulk": True,
                "stock_results": [],
                "stock_ids": self.stock_ids,
                "error": str(exc),
            }


def run_calendar_slice_enumeration_payload(job_payload: Dict[str, Any]) -> Dict[str, Any]:
    return CalendarSliceEnumeratorWorker(job_payload).run()


__all__ = ["CalendarSliceEnumeratorWorker", "run_calendar_slice_enumeration_payload"]
