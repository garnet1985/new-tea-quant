#!/usr/bin/env python3
"""Tag calendar_slice worker（BacktestEngine sliced 编排入口）。"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional
import logging

from core.modules.tag.engines.sliced.runtime.orchestrator import TagCalendarSliceOrchestrator

logger = logging.getLogger(__name__)


class TagCalendarSliceWorker:
    """Single bulk job: orchestrator + Reader Lane + Compute Lane."""

    def __init__(
        self,
        job_payload: Dict[str, Any],
        *,
        on_slice_tag_values: Optional[Callable[[List[Dict[str, Any]]], None]] = None,
    ):
        self.job_payload = job_payload
        self._on_slice_tag_values = on_slice_tag_values
        self.entity_ids = [
            str(e).strip() for e in (job_payload.get("entity_ids") or []) if str(e).strip()
        ]
        if not self.entity_ids:
            raise ValueError("TagCalendarSliceWorker 缺少 entity_ids")

    def run(self) -> Dict[str, Any]:
        try:
            return TagCalendarSliceOrchestrator(
                self.job_payload,
                on_slice_tag_values=self._on_slice_tag_values,
            ).run()
        except Exception as exc:
            logger.error("tag calendar_slice failed: %s", exc, exc_info=True)
            return {
                "success": False,
                "bulk": True,
                "tag_values": [],
                "entity_count": len(self.entity_ids),
                "error": str(exc),
            }


def run_tag_calendar_slice_payload(
    job_payload: Dict[str, Any],
    *,
    on_slice_tag_values: Optional[Callable[[List[Dict[str, Any]]], None]] = None,
) -> Dict[str, Any]:
    return TagCalendarSliceWorker(
        job_payload,
        on_slice_tag_values=on_slice_tag_values,
    ).run()


__all__ = ["TagCalendarSliceWorker", "run_tag_calendar_slice_payload"]
