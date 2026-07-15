"""Shared preload_depth sizing (canonical name for feed-ahead / queue depth).

``preload_depth`` is the single knob for how many slices may run ahead of
compute. ``queue_capacity`` is always set equal to ``preload_depth`` at plan
time (Queue maxsize = ahead gate). Reader worker count is independent and
fixed to the standby pool size.
"""
from __future__ import annotations

import math
from typing import Optional

MAX_PRELOAD_DEPTH = 8
_IO_COMPUTE_SAFETY = 1.15
_DEFAULT_T_IO_SEC = 2.0
_DEFAULT_T_COMPUTE_SEC = 0.05


def ideal_preload_from_timings(t_io_sec: float, t_compute_sec: float) -> int:
    """``ceil((t_io / t_compute) * safety)`` capped to ``MAX_PRELOAD_DEPTH``."""
    t_io = max(float(t_io_sec), 0.001)
    t_compute = max(float(t_compute_sec), 0.001)
    raw = math.ceil((t_io / t_compute) * _IO_COMPUTE_SAFETY)
    return max(1, min(MAX_PRELOAD_DEPTH, raw))


def preload_depth_from_memory(
    *,
    memory_budget_mb: float,
    mb_per_in_flight_slice: Optional[float] = None,
    mb_per_slice: Optional[float] = None,
    carry_reserve_mb: float = 128.0,
    compute_reserve_mb: float = 64.0,
) -> int:
    """How many ahead slots fit after reserving carry + one compute slice."""
    per_raw = mb_per_in_flight_slice if mb_per_in_flight_slice is not None else mb_per_slice
    usable = max(
        0.0,
        float(memory_budget_mb) - float(carry_reserve_mb) - float(compute_reserve_mb),
    )
    per = max(float(per_raw if per_raw is not None else 1.0), 1.0)
    return max(1, min(MAX_PRELOAD_DEPTH, int(usable / per)))


def resolve_preload_depth(
    *,
    t_io_sec: Optional[float],
    t_compute_sec: Optional[float],
    memory_budget_mb: float,
    mb_per_in_flight_slice: float,
    prefetch_enabled: bool = True,
) -> int:
    """Time-ratio ideal, then clip by memory budget."""
    if not prefetch_enabled:
        return 1
    io_ideal = ideal_preload_from_timings(
        t_io_sec if t_io_sec is not None else _DEFAULT_T_IO_SEC,
        t_compute_sec if t_compute_sec is not None else _DEFAULT_T_COMPUTE_SEC,
    )
    mem_ideal = preload_depth_from_memory(
        memory_budget_mb=memory_budget_mb,
        mb_per_in_flight_slice=mb_per_in_flight_slice,
    )
    return max(1, min(io_ideal, mem_ideal, MAX_PRELOAD_DEPTH))


__all__ = [
    "MAX_PRELOAD_DEPTH",
    "ideal_preload_from_timings",
    "preload_depth_from_memory",
    "resolve_preload_depth",
]
