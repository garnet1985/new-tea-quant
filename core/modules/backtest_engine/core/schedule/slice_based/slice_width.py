"""Resolve formal slice width (open-date count per slice).

Principles (priority high → low):
1. Hard OOM → fail (do not run).
2. Start compute ASAP: prefer single-slice cover of ``min_required``.
3. Keep slice size in a feedback-friendly band (FLOOR … UX hard max).

``in_flight`` (concurrent resident slices) is dynamic:
``max(2, reader_workers + compute_processes)``.
"""
from __future__ import annotations

import math
from typing import Optional

DEFAULT_SLICE_OPEN_DAYS_FLOOR = 20
DEFAULT_SLICE_OPEN_DAYS_UX_MAX = 500
SLICE_WIDTH_SAFETY = 0.8
MIN_IN_FLIGHT = 2
MAX_PRELOAD_DEPTH = 8
DEFAULT_PRELOAD_DEPTH = 2


class SliceWidthError(ValueError):
    """Slice width cannot be resolved without OOM / readiness risk."""


def normalize_in_flight(in_flight: int) -> int:
    return max(MIN_IN_FLIGHT, int(in_flight))


def memory_cap_open_days(
    *,
    available_mb: float,
    in_flight: int,
    mb_per_open_day: float,
    discount: float = SLICE_WIDTH_SAFETY,
    ux_hard_max: int = DEFAULT_SLICE_OPEN_DAYS_UX_MAX,
) -> int:
    """Max open days per slice afforded by memory (then UX hard max)."""
    flight = normalize_in_flight(in_flight)
    per_day = max(float(mb_per_open_day), 1e-6)
    budget = max(float(available_mb), 0.0)
    raw = math.floor(budget / flight / per_day * float(discount))
    return max(0, min(int(ux_hard_max), int(raw)))


def resolve_slice_open_days(
    *,
    available_mb: float,
    in_flight: int,
    mb_per_open_day: float,
    min_required: int,
    total_open_days: int,
    floor: int = DEFAULT_SLICE_OPEN_DAYS_FLOOR,
    ux_hard_max: int = DEFAULT_SLICE_OPEN_DAYS_UX_MAX,
    discount: float = SLICE_WIDTH_SAFETY,
    explicit_width: Optional[int] = None,
) -> int:
    """Pick formal ``slice_open_days`` or raise ``SliceWidthError``.

    When ``explicit_width`` is set, that value is used after the same
    feasibility checks (principle 1).
    """
    flight = normalize_in_flight(in_flight)
    floor_n = max(1, int(floor))
    ux_max = max(floor_n, int(ux_hard_max))
    need_required = max(0, int(min_required))
    total = max(0, int(total_open_days))

    cap = memory_cap_open_days(
        available_mb=available_mb,
        in_flight=flight,
        mb_per_open_day=mb_per_open_day,
        discount=discount,
        ux_hard_max=ux_max,
    )

    if explicit_width is not None:
        width = max(1, int(explicit_width))
        _assert_feasible(
            width=width,
            floor=floor_n,
            cap=cap,
            in_flight=flight,
            min_required=need_required,
            explicit=True,
        )
        return _maybe_split_for_calendar(
            width,
            total_open_days=total,
            floor=floor_n,
            cap=cap,
            in_flight=flight,
            min_required=need_required,
        )

    if cap < floor_n:
        raise SliceWidthError(
            f"内存不足以支撑最小片宽：cap={cap} < floor={floor_n} "
            f"(available_mb={available_mb:.1f}, in_flight={flight}, "
            f"mb_per_open_day={mb_per_open_day:.4f})"
        )
    if flight * cap < need_required:
        raise SliceWidthError(
            f"并存片总宽度仍盖不住 min_required："
            f"in_flight({flight}) * cap({cap}) < min_required({need_required})；"
            f"存在 OOM / 无法开算风险"
        )

    need = max(floor_n, need_required)
    if need <= cap:
        width = need
    else:
        width = cap

    return _maybe_split_for_calendar(
        width,
        total_open_days=total,
        floor=floor_n,
        cap=cap,
        in_flight=flight,
        min_required=need_required,
    )


def resolve_reader_queue_depth(
    *,
    available_mb: float,
    mb_per_slice: float,
    compute_processes: int = 1,
    current_depth: Optional[int] = None,
    max_depth: int = MAX_PRELOAD_DEPTH,
    high_watermark: float = 0.85,
    low_watermark: float = 0.60,
    prefetch_enabled: bool = True,
) -> int:
    """Size reader queue (``preload_depth``) from per-slice MB; width stays fixed.

    - ``current_depth is None``: initial ideal from memory only.
    - Otherwise: scale down under high pressure / up under low watermark.
    """
    if not prefetch_enabled:
        return 1

    cap_depth = max(1, min(int(max_depth), MAX_PRELOAD_DEPTH))
    compute_n = max(1, int(compute_processes))
    per = max(float(mb_per_slice), 1.0)
    budget = max(float(available_mb), 0.0)
    usable = max(0.0, budget * float(high_watermark) - compute_n * per)
    ideal = max(1, min(cap_depth, int(usable / per)))

    if current_depth is None:
        return ideal

    cur = max(1, min(cap_depth, int(current_depth)))
    resident = (cur + compute_n) * per
    high = budget * float(high_watermark)
    low = budget * float(low_watermark)

    if resident > high:
        return max(1, min(ideal, cur - 1))
    if resident < low and ideal > cur:
        return min(cap_depth, cur + 1, ideal)
    return min(cap_depth, max(1, min(cur, ideal)))


def _assert_feasible(
    *,
    width: int,
    floor: int,
    cap: int,
    in_flight: int,
    min_required: int,
    explicit: bool,
) -> None:
    if width < floor:
        raise SliceWidthError(
            f"{'显式' if explicit else ''}片宽 {width} 低于最小片宽 floor={floor}"
        )
    if width > cap and cap >= floor:
        raise SliceWidthError(
            f"{'显式' if explicit else ''}片宽 {width} 超过内存/UX 上限 cap={cap}"
        )
    if in_flight * width < min_required:
        raise SliceWidthError(
            f"并存片总宽度盖不住 min_required："
            f"in_flight({in_flight}) * width({width}) < min_required({min_required})"
        )


def _maybe_split_for_calendar(
    width: int,
    *,
    total_open_days: int,
    floor: int,
    cap: int,
    in_flight: int,
    min_required: int,
) -> int:
    """Prefer ≥2 formal slices on long calendars; short windows may stay at 1."""
    total = max(0, int(total_open_days))
    if total < 2:
        return width
    if math.ceil(total / max(width, 1)) >= 2:
        return width

    adjusted = max(floor, int(math.ceil(total / 2.0)))
    if adjusted > cap:
        raise SliceWidthError(
            f"为凑满 ≥2 个正式片需 width={adjusted}，但超过 cap={cap}"
        )
    if in_flight * adjusted < min_required:
        raise SliceWidthError(
            f"为凑满 ≥2 个正式片缩小后仍盖不住 min_required："
            f"in_flight({in_flight}) * width({adjusted}) < min_required({min_required})"
        )
    return adjusted


__all__ = [
    "DEFAULT_PRELOAD_DEPTH",
    "DEFAULT_SLICE_OPEN_DAYS_FLOOR",
    "DEFAULT_SLICE_OPEN_DAYS_UX_MAX",
    "MAX_PRELOAD_DEPTH",
    "MIN_IN_FLIGHT",
    "SLICE_WIDTH_SAFETY",
    "SliceWidthError",
    "memory_cap_open_days",
    "normalize_in_flight",
    "resolve_reader_queue_depth",
    "resolve_slice_open_days",
]
