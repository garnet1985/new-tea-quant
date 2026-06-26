#!/usr/bin/env python3
"""calendar_slice Runtime Planner：auto 片宽 / reader / preload depth。"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, Optional

from core.infra.job_pipeline.profile import WorkerProfiles, resolve_pipeline_workers
from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.runtime.memory_budget import (
    resolve_calendar_slice_memory_budget_mb,
)
from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.runtime.runtime_plan import (
    CalendarSliceRuntimePlan,
)
from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.slice_plan import (
    is_auto_setting as slice_is_auto,
    resolve_auto_slice_open_days,
)
from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.runtime.settings import (
    CalendarSliceRuntimeSettings,
    is_auto_setting,
)

logger = logging.getLogger(__name__)

_MAX_READER_WORKERS = 8
_MAX_QUEUE_DEPTH = 8
_DEFAULT_MB_PER_SLICE = 400.0
_DEFAULT_T_IO_SEC = 2.0
_DEFAULT_T_COMPUTE_SEC = 0.05
_IO_COMPUTE_SAFETY = 1.15


def ideal_preload_from_timings(t_io_sec: float, t_compute_sec: float) -> int:
    t_io = max(float(t_io_sec), 0.001)
    t_compute = max(float(t_compute_sec), 0.001)
    raw = math.ceil((t_io / t_compute) * _IO_COMPUTE_SAFETY)
    return max(1, min(_MAX_QUEUE_DEPTH, raw))


def preload_depth_from_memory(
    *,
    memory_budget_mb: float,
    mb_per_slice: float,
    carry_reserve_mb: float,
    compute_reserve_mb: float,
) -> int:
    usable = max(
        0.0,
        float(memory_budget_mb) - float(carry_reserve_mb) - float(compute_reserve_mb),
    )
    per = max(float(mb_per_slice), 1.0)
    return max(1, min(_MAX_QUEUE_DEPTH, int(usable / per)))


def resolve_reader_workers(
    *,
    raw: Any,
    duckdb: bool,
    io_parallel_hint: int,
    system_process_cap: int,
) -> int:
    if duckdb:
        return 1
    if not is_auto_setting(raw):
        try:
            return max(1, min(_MAX_READER_WORKERS, int(raw)))
        except (TypeError, ValueError):
            return 1
    reader_cap = max(1, int(system_process_cap) - 1)
    return max(1, min(_MAX_READER_WORKERS, io_parallel_hint, reader_cap))


def resolve_system_process_cap(worker_id: str = WorkerProfiles.ENUMERATOR) -> int:
    return max(1, resolve_pipeline_workers(worker_id=worker_id))


def is_duckdb_backend() -> bool:
    try:
        from core.infra.project_context import ProjectContextManager

        bt = str(ctx.load_database_config().get("database_type") or "").lower()
        return "duck" in bt
    except Exception:
        return False


def _parse_min_required_records(job_payload: Dict[str, Any]) -> int:
    block = (job_payload.get("settings") or {}).get("data") or {}
    if "min_required_records" not in block:
        return 100
    return max(1, int(block["min_required_records"]))


def build_runtime_plan(
    job_payload: Dict[str, Any],
    *,
    open_days_total: int,
    settings: Optional[CalendarSliceRuntimeSettings] = None,
    mb_per_slice: Optional[float] = None,
    t_io_sec: Optional[float] = None,
    t_compute_sec: Optional[float] = None,
    worker_profile: str = WorkerProfiles.ENUMERATOR,
) -> CalendarSliceRuntimePlan:
    settings = settings or CalendarSliceRuntimeSettings.from_worker_profile()
    _ = _parse_min_required_records(job_payload)

    raw_slice = job_payload.get("slice_open_days")
    if not slice_is_auto(raw_slice):
        raise ValueError(
            f"calendar_slice job 启动时 slice_open_days 须为 'auto'，收到 {raw_slice!r}"
        )

    budget_mb = resolve_calendar_slice_memory_budget_mb()
    mb = float(mb_per_slice if mb_per_slice is not None else _DEFAULT_MB_PER_SLICE)
    t_io = float(t_io_sec if t_io_sec is not None else _DEFAULT_T_IO_SEC)
    t_compute = float(t_compute_sec if t_compute_sec is not None else _DEFAULT_T_COMPUTE_SEC)

    slice_days = resolve_auto_slice_open_days(
        mb_per_slice=mb,
        memory_budget_mb=budget_mb,
        open_days_total=open_days_total,
    )

    io_ideal = ideal_preload_from_timings(t_io, t_compute)
    mem_ideal = preload_depth_from_memory(
        memory_budget_mb=budget_mb,
        mb_per_slice=mb,
        carry_reserve_mb=128.0,
        compute_reserve_mb=64.0,
    )
    ideal_preload = max(1, min(io_ideal, mem_ideal, _MAX_QUEUE_DEPTH))

    duckdb = is_duckdb_backend()
    system_cap = resolve_system_process_cap(worker_profile)
    reader_workers = resolve_reader_workers(
        raw=settings.reader_workers_raw,
        duckdb=duckdb,
        io_parallel_hint=ideal_preload,
        system_process_cap=system_cap,
    )

    if is_auto_setting(settings.queue_depth_raw):
        queue_capacity = max(ideal_preload, reader_workers if settings.prefetch_enabled else 1)
        queue_capacity = max(1, min(_MAX_QUEUE_DEPTH, queue_capacity))
        current_preload = ideal_preload
    else:
        queue_capacity = max(1, min(_MAX_QUEUE_DEPTH, settings.queue_depth))
        current_preload = min(ideal_preload, queue_capacity) if settings.prefetch_enabled else 1

    if not settings.prefetch_enabled:
        ideal_preload = 1
        current_preload = 1
        queue_capacity = 1
        reader_workers = 1

    plan = CalendarSliceRuntimePlan(
        slice_open_days=slice_days,
        memory_budget_mb=budget_mb,
        reader_workers=reader_workers,
        ideal_preload_ceiling=ideal_preload,
        current_preload_depth=current_preload,
        queue_capacity=queue_capacity,
        mb_per_slice=mb,
        prefetch_enabled=settings.prefetch_enabled,
    )
    logger.info("[calendar_slice:plan] initial %s", plan.to_dict())
    return plan


__all__ = [
    "_parse_min_required_records",
    "build_runtime_plan",
    "ideal_preload_from_timings",
    "is_duckdb_backend",
    "preload_depth_from_memory",
    "resolve_reader_workers",
    "resolve_system_process_cap",
]
