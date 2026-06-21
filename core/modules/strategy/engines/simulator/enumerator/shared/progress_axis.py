#!/usr/bin/env python3
"""跨 execution_mode 的进度轴与 job 元数据。"""

from __future__ import annotations

from typing import Any, Dict, List

from core.modules.strategy.engines.simulator.enumerator.stock_based.progress import (
    ENTITY_PROGRESS_MODE_STOCK,
    normalize_entity_progress_mode,
    progress_axis_for_entity_mode,
)


def progress_axis_for_calendar_mode(mode: str) -> str:
    from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.progress import (
        CALENDAR_PROGRESS_MODE_SLICE,
        normalize_calendar_progress_mode,
    )

    if normalize_calendar_progress_mode(mode) == CALENDAR_PROGRESS_MODE_SLICE:
        return "calendar_slice"
    return "calendar_open_date"


def enumeration_progress_metadata(jobs: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not jobs:
        return {}
    job = jobs[0]
    if job.get("enumeration_execution_mode") == "calendar_slice":
        mode = str(job.get("calendar_progress_mode") or "open_date")
        return {
            "progress_axis": progress_axis_for_calendar_mode(mode),
            "calendar_progress_mode": mode,
            "enumeration_execution_mode": "calendar_slice",
        }
    mode = str(job.get("entity_progress_mode") or ENTITY_PROGRESS_MODE_STOCK)
    return {
        "progress_axis": progress_axis_for_entity_mode(mode),
        "entity_progress_mode": mode,
        "enumeration_execution_mode": "entity_timeline",
    }


__all__ = [
    "enumeration_progress_metadata",
    "progress_axis_for_calendar_mode",
]
