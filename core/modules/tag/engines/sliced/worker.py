#!/usr/bin/env python3
"""Tag calendar_slice worker（JobPipeline 子进程入口）。"""

from __future__ import annotations

from typing import Any, Dict
import logging

from core.modules.tag.engines.sliced.runtime.orchestrator import TagCalendarSliceOrchestrator

logger = logging.getLogger(__name__)


class TagCalendarSliceWorker:
    """Single bulk job: orchestrator + Reader Lane + Compute Lane."""

    def __init__(self, job_payload: Dict[str, Any]):
        self.job_payload = job_payload
        self.entity_ids = [
            str(e).strip() for e in (job_payload.get("entity_ids") or []) if str(e).strip()
        ]
        if not self.entity_ids:
            raise ValueError("TagCalendarSliceWorker 缺少 entity_ids")

    def run(self) -> Dict[str, Any]:
        try:
            return TagCalendarSliceOrchestrator(self.job_payload).run()
        except Exception as exc:
            logger.error("tag calendar_slice failed: %s", exc, exc_info=True)
            return {
                "success": False,
                "bulk": True,
                "tag_values": [],
                "entity_count": len(self.entity_ids),
                "error": str(exc),
            }


def run_tag_calendar_slice_payload(job_payload: Dict[str, Any]) -> Dict[str, Any]:
    return TagCalendarSliceWorker(job_payload).run()


__all__ = ["TagCalendarSliceWorker", "run_tag_calendar_slice_payload"]
