#!/usr/bin/env python3
"""Calendar slice enumeration progress reporting."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Sequence

from core.modules.strategy.engines.simulator.enumerator.calendar_slice.slice_plan import (
    plan_calendar_slices,
)
from core.modules.strategy.engines.simulator.enumerator.live_progress import (
    publish_enumeration_execute_progress,
)
from core.modules.strategy.engines.simulator.enumerator.progress import (
    progress_axis_for_calendar_mode,
)

logger = logging.getLogger(__name__)

CALENDAR_PROGRESS_MODE_SLICE = "slice"
CALENDAR_PROGRESS_MODE_OPEN_DATE = "open_date"
KNOWN_CALENDAR_PROGRESS_MODES = frozenset(
    {CALENDAR_PROGRESS_MODE_SLICE, CALENDAR_PROGRESS_MODE_OPEN_DATE}
)


def normalize_calendar_progress_mode(raw: Any) -> str:
    mode = str(raw or CALENDAR_PROGRESS_MODE_OPEN_DATE).strip().lower()
    if mode in KNOWN_CALENDAR_PROGRESS_MODES:
        return mode
    return CALENDAR_PROGRESS_MODE_OPEN_DATE


def resolve_calendar_progress_plan(
    *,
    open_dates: Sequence[str],
    slice_open_days: int,
    progress_mode: str,
) -> Dict[str, Any]:
    slices = plan_calendar_slices(open_dates, slice_open_days)
    mode = normalize_calendar_progress_mode(progress_mode)
    total = len(slices) if mode == CALENDAR_PROGRESS_MODE_SLICE else len(open_dates)
    return {
        "calendar_progress_mode": mode,
        "calendar_progress_total": max(1, int(total)),
        "calendar_slice_count": len(slices),
        "calendar_open_date_count": len(open_dates),
    }


def filter_open_dates_in_range(
    open_dates: Sequence[str],
    start_date: str,
    end_date: str,
) -> List[str]:
    start = str(start_date or "").strip()
    end = str(end_date or "").strip()
    return [d for d in open_dates if start <= str(d).strip() <= end]


class CalendarSliceProgressReporter:
    """Worker 子进程：按 slice / open_date 上报进度（侧车 + 信封 + 终端）。"""

    __slots__ = (
        "_done",
        "_elapsed_base",
        "_mode",
        "_run_id",
        "_strategy_name",
        "_total",
    )

    def __init__(
        self,
        job_payload: Dict[str, Any],
        *,
        total: int,
        mode: str,
        run_started_at: Optional[float] = None,
    ) -> None:
        self._total = max(1, int(total))
        self._mode = normalize_calendar_progress_mode(mode)
        self._done = 0
        self._elapsed_base = float(run_started_at if run_started_at is not None else time.time())
        self._strategy_name = str(job_payload.get("workbench_strategy_name") or "").strip()
        self._run_id = str(job_payload.get("workbench_run_id") or "").strip()

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def total(self) -> int:
        return self._total

    @property
    def done(self) -> int:
        return self._done

    def seed(self) -> None:
        """启动时写入 0%，避免长时间无侧车。"""
        self._emit(done=self._done, pct=0, detail="start", phase="start")

    def tick(
        self,
        *,
        slice_id: str = "",
        as_of_date: str = "",
        phase: str = "",
    ) -> None:
        self._done = min(self._total, self._done + 1)
        pct = min(100, int(self._done * 100 / self._total))
        detail = slice_id or as_of_date or phase or "-"
        self._emit(done=self._done, pct=pct, detail=detail, phase=phase, slice_id=slice_id, as_of_date=as_of_date)

    def finish(self) -> Dict[str, Any]:
        elapsed = max(0.0, time.time() - self._elapsed_base)
        self._emit(
            done=self._total,
            pct=100,
            detail="finish",
            phase="finish",
            elapsed_seconds=round(elapsed, 2),
        )
        return {
            "mode": self._mode,
            "total": self._total,
            "done": self._total,
            "elapsed_seconds": round(elapsed, 2),
        }

    def _emit(
        self,
        *,
        done: int,
        pct: int,
        detail: str,
        phase: str = "",
        slice_id: str = "",
        as_of_date: str = "",
        elapsed_seconds: Optional[float] = None,
    ) -> None:
        elapsed = (
            float(elapsed_seconds)
            if elapsed_seconds is not None
            else max(0.0, time.time() - self._elapsed_base)
        )
        logger.info(
            "[calendar_slice] 进度 %s/%s (%s%%) %s=%s 已用 %.1fs",
            done,
            self._total,
            pct,
            self._mode,
            detail,
            elapsed,
        )
        sidecar_extra: Dict[str, Any] = {
            "calendar_progress_mode": self._mode,
            "progress_axis": progress_axis_for_calendar_mode(self._mode),
            "elapsed_seconds": round(elapsed, 2),
        }
        if slice_id:
            sidecar_extra["calendar_slice_id"] = slice_id
        if as_of_date:
            sidecar_extra["calendar_as_of_date"] = as_of_date
        if phase:
            sidecar_extra["calendar_phase"] = phase

        publish_enumeration_execute_progress(
            strategy_name=self._strategy_name,
            run_id=self._run_id,
            done=done,
            total=self._total,
            sidecar_extra=sidecar_extra,
        )


__all__ = [
    "CALENDAR_PROGRESS_MODE_OPEN_DATE",
    "CALENDAR_PROGRESS_MODE_SLICE",
    "CalendarSliceProgressReporter",
    "KNOWN_CALENDAR_PROGRESS_MODES",
    "filter_open_dates_in_range",
    "normalize_calendar_progress_mode",
    "resolve_calendar_progress_plan",
]
