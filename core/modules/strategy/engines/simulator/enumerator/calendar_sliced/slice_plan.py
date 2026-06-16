#!/usr/bin/env python3
"""Calendar slice planning helpers (MVP: no memory probe)."""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple

from core.modules.strategy.engines.shared.data_classes.strategy_settings.simulation_settings import (
    MAX_SLICE_OPEN_DAYS,
)


@dataclass(frozen=True)
class CalendarSliceDescriptor:
    slice_id: str
    slice_index: int
    window_start: str
    window_end: str
    open_dates: Tuple[str, ...]


MIN_PLANNER_SLICE_OPEN_DAYS = 50
# dispatch 阶段进度估算占位；运行时 planner 会 refine 为实际片宽
SLICE_STEPS_AUTO_ESTIMATE = MIN_PLANNER_SLICE_OPEN_DAYS


def is_auto_setting(value: Any) -> bool:
    return str(value or "").strip().lower() == "auto"


def resolve_slice_width_floor() -> int:
    return MIN_PLANNER_SLICE_OPEN_DAYS


def resolve_auto_slice_open_days(
    *,
    mb_per_slice: float,
    memory_budget_mb: float,
    open_days_total: int,
) -> int:
    _ = open_days_total
    floor = resolve_slice_width_floor()
    if mb_per_slice <= 0:
        return floor
    usable = max(0.0, memory_budget_mb - 192.0)
    max_slices_in_mem = max(1, int(usable / mb_per_slice))
    if max_slices_in_mem >= 3:
        target = max(floor, min(63, MAX_SLICE_OPEN_DAYS))
    else:
        target = floor
    return max(floor, min(MAX_SLICE_OPEN_DAYS, target))


def clamp_resolved_slice_open_days(days: int) -> int:
    """运行时已 resolve 的整数片宽，只做上下界 clamp。"""
    floor = resolve_slice_width_floor()
    return max(floor, min(MAX_SLICE_OPEN_DAYS, max(1, int(days))))


def is_first_open_of_month(as_of_date: str, open_dates: Sequence[str]) -> bool:
    d = str(as_of_date or "").strip()
    if not d or not open_dates:
        return False
    idx = bisect_left(open_dates, d)
    if idx >= len(open_dates) or open_dates[idx] != d:
        return False
    if idx == 0:
        return True
    return str(open_dates[idx - 1])[:6] != d[:6]


def is_last_open_of_month(as_of_date: str, open_dates: Sequence[str]) -> bool:
    d = str(as_of_date or "").strip()
    if not d or not open_dates:
        return False
    idx = bisect_left(open_dates, d)
    if idx >= len(open_dates) or open_dates[idx] != d:
        return False
    if idx + 1 >= len(open_dates):
        return True
    return str(open_dates[idx + 1])[:6] != d[:6]


def plan_calendar_slices(
    open_dates: Sequence[str],
    slice_open_days: int,
) -> List[CalendarSliceDescriptor]:
    dates = [str(d).strip() for d in open_dates if str(d).strip()]
    if not dates:
        return []
    size = max(1, int(slice_open_days))
    slices: List[CalendarSliceDescriptor] = []
    for idx in range(0, len(dates), size):
        chunk = tuple(dates[idx : idx + size])
        if not chunk:
            continue
        slices.append(
            CalendarSliceDescriptor(
                slice_id=f"slice_{len(slices)}",
                slice_index=len(slices),
                window_start=chunk[0],
                window_end=chunk[-1],
                open_dates=chunk,
            )
        )
    return slices


def build_calendar_slice_dispatch_job(
    *,
    strategy_name: str,
    settings_payload: Dict[str, Any],
    output_dir: str,
    worker_ref: Dict[str, str],
    stock_ids: List[str],
    start_date: str,
    end_date: str,
) -> Dict[str, Any]:
    ids = [str(s).strip() for s in stock_ids if str(s).strip()]
    if not ids:
        raise ValueError("calendar_slice 需要非空 stock_ids")
    return {
        "job_id": "calendar_slice",
        "enumeration_execution_mode": "calendar_slice",
        "slice_open_days": "auto",
        "stock_ids": ids,
        "strategy_name": strategy_name,
        "settings": settings_payload,
        "start_date": start_date,
        "end_date": end_date,
        "output_dir": output_dir,
        "worker_module_path": worker_ref["worker_module_path"],
        "worker_class_name": worker_ref["worker_class_name"],
        "worker_file_path": str(worker_ref.get("worker_file_path") or ""),
    }


__all__ = [
    "CalendarSliceDescriptor",
    "MIN_PLANNER_SLICE_OPEN_DAYS",
    "SLICE_STEPS_AUTO_ESTIMATE",
    "build_calendar_slice_dispatch_job",
    "clamp_resolved_slice_open_days",
    "is_auto_setting",
    "is_first_open_of_month",
    "is_last_open_of_month",
    "plan_calendar_slices",
    "resolve_auto_slice_open_days",
    "resolve_slice_width_floor",
]
