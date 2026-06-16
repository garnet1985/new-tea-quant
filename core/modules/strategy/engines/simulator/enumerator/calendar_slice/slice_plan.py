#!/usr/bin/env python3
"""Calendar slice planning helpers (MVP: no memory probe)."""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple

from core.modules.strategy.engines.shared.data_classes.strategy_settings.simulation_settings import (
    DEFAULT_SLICE_OPEN_DAYS,
    MAX_SLICE_OPEN_DAYS,
    MIN_SLICE_OPEN_DAYS,
)


@dataclass(frozen=True)
class CalendarSliceDescriptor:
    slice_id: str
    slice_index: int
    window_start: str
    window_end: str
    open_dates: Tuple[str, ...]


MIN_PLANNER_SLICE_OPEN_DAYS = 50


def is_auto_setting(value: Any) -> bool:
    if value is None:
        return False
    return str(value).strip().lower() == "auto"


def auto_slice_open_days_floor(min_required_records: int) -> int:
    return max(MIN_PLANNER_SLICE_OPEN_DAYS, max(1, int(min_required_records or 0)))


def reject_if_min_records_exceeds_max_slice(min_required_records: int) -> None:
    floor = max(1, int(min_required_records or 0))
    if floor > MAX_SLICE_OPEN_DAYS:
        raise ValueError(
            f"data.min_required_records={floor} 超过 calendar_slice 最大片宽 "
            f"{MAX_SLICE_OPEN_DAYS}，无法执行"
        )


def resolve_auto_slice_open_days(
    *,
    min_required_records: int,
    mb_per_slice: float,
    memory_budget_mb: float,
    open_days_total: int,
) -> int:
    """
    auto 片宽：在 [floor, MAX] 内按 memory 与片数 tradeoff 选取。

    目标：单片内存可行且片数不过多（fixed cost）；v1 用 memory 反推上限，再与 floor 取 max。
    """
    _ = open_days_total
    floor = auto_slice_open_days_floor(min_required_records)
    if mb_per_slice <= 0:
        return floor
    # 预算内至少容 2 片 preload + carry/compute 预留
    usable = max(0.0, memory_budget_mb - 192.0)
    max_slices_in_mem = max(1, int(usable / mb_per_slice))
    if max_slices_in_mem >= 3:
        # 内存充裕：用较宽片减少 dispatch 次数（默认 63 或 floor 较大者）
        target = max(floor, min(63, MAX_SLICE_OPEN_DAYS))
    else:
        # 内存紧：保持 floor（窄片）
        target = floor
    return max(floor, min(MAX_SLICE_OPEN_DAYS, target))


def clamp_slice_open_days(
    raw_days: Any,
    *,
    min_required_records: int,
) -> int:
    """Clamp configured slice_open_days without memory probe (MVP)."""
    reject_if_min_records_exceeds_max_slice(min_required_records)
    if is_auto_setting(raw_days):
        return auto_slice_open_days_floor(min_required_records)
    try:
        days = int(raw_days if raw_days not in (None, "") else DEFAULT_SLICE_OPEN_DAYS)
    except (TypeError, ValueError) as e:
        raise ValueError("simulation.slice_open_days 须为整数或 auto") from e
    floor = auto_slice_open_days_floor(min_required_records)
    ceiling = MAX_SLICE_OPEN_DAYS
    if days < floor:
        return floor
    if days > ceiling:
        return ceiling
    return days


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
    """当月最后一个开市日。"""
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
    """Split sorted open dates into fixed-size calendar slices."""
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
    slice_open_days: Any,
) -> Dict[str, Any]:
    ids = [str(s).strip() for s in stock_ids if str(s).strip()]
    if not ids:
        raise ValueError("calendar_slice 需要非空 stock_ids")
    return {
        "job_id": "calendar_slice",
        "enumeration_execution_mode": "calendar_slice",
        "slice_open_days": slice_open_days,
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
    "auto_slice_open_days_floor",
    "build_calendar_slice_dispatch_job",
    "clamp_slice_open_days",
    "is_auto_setting",
    "is_first_open_of_month",
    "is_last_open_of_month",
    "plan_calendar_slices",
    "reject_if_min_records_exceeds_max_slice",
    "resolve_auto_slice_open_days",
]
