#!/usr/bin/env python3
"""calendar_slice Runtime Planner：auto 片宽 / reader / preload depth。"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, Optional, Union

from core.infra.job_pipeline.profile import WorkerProfiles, resolve_pipeline_workers
from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.runtime.memory_budget import (
    resolve_calendar_slice_memory_budget_mb,
)
from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.runtime.runtime_plan import (
    CalendarSliceRuntimePlan,
)
from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.runtime.settings import (
    CalendarSliceRuntimeSettings,
    is_auto_setting,
)
from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.slice_plan import (
    MAX_SLICE_OPEN_DAYS,
    MIN_PLANNER_SLICE_OPEN_DAYS,
    auto_slice_open_days_floor,
    reject_if_min_records_exceeds_max_slice,
    resolve_auto_slice_open_days,
)

logger = logging.getLogger(__name__)

_MAX_READER_WORKERS = 8
_MAX_QUEUE_DEPTH = 8
_DEFAULT_MB_PER_SLICE = 400.0
_DEFAULT_T_IO_SEC = 2.0
_DEFAULT_T_COMPUTE_SEC = 0.05
_IO_COMPUTE_SAFETY = 1.15


def ideal_preload_from_timings(t_io_sec: float, t_compute_sec: float) -> int:
    """pipeline 理想 preload 片数 ≈ T_io / T_compute（含 safety）。"""
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
    """carry 不计入 preload；仅预算 preload 片数。"""
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
    # auto: IO 并行不超过 system_cap - 1（留 1 给 compute）
    reader_cap = max(1, int(system_process_cap) - 1)
    return max(1, min(_MAX_READER_WORKERS, io_parallel_hint, reader_cap))


def resolve_system_process_cap() -> int:
    return max(1, resolve_pipeline_workers(worker_id=WorkerProfiles.ENUMERATOR))


def is_duckdb_backend() -> bool:
    try:
        from core.infra.project_context import ConfigManager

        bt = str(ConfigManager.load_database_config().get("database_type") or "").lower()
        return "duck" in bt
    except Exception:
        return False


def resolve_slice_open_days_for_job(
    raw: Any,
    *,
    min_required_records: int,
    mb_per_slice: float,
    memory_budget_mb: float,
    open_days_total: int,
) -> int:
    reject_if_min_records_exceeds_max_slice(min_required_records)
    if is_auto_setting(raw):
        return resolve_auto_slice_open_days(
            min_required_records=min_required_records,
            mb_per_slice=mb_per_slice,
            memory_budget_mb=memory_budget_mb,
            open_days_total=open_days_total,
        )
    try:
        days = int(raw)
    except (TypeError, ValueError):
        days = auto_slice_open_days_floor(min_required_records)
    floor = auto_slice_open_days_floor(min_required_records)
    return max(floor, min(MAX_SLICE_OPEN_DAYS, days))


def build_runtime_plan(
    job_payload: Dict[str, Any],
    *,
    open_days_total: int,
    settings: Optional[CalendarSliceRuntimeSettings] = None,
    mb_per_slice: Optional[float] = None,
    t_io_sec: Optional[float] = None,
    t_compute_sec: Optional[float] = None,
) -> CalendarSliceRuntimePlan:
    """job 启动时构建 plan；探针 refine 在首片后调用 plan.refine_from_timings()。"""
    settings = settings or CalendarSliceRuntimeSettings.from_job_payload(job_payload)
    min_records = 100
    try:
        block = (job_payload.get("settings") or {}).get("data") or {}
        min_records = int(block.get("min_required_records") or 100)
    except (TypeError, ValueError):
        pass
    min_records = max(1, min_records)

    raw_slice = job_payload.get("slice_open_days")
    budget_mb = resolve_calendar_slice_memory_budget_mb()
    mb = float(mb_per_slice if mb_per_slice is not None else _DEFAULT_MB_PER_SLICE)
    t_io = float(t_io_sec if t_io_sec is not None else _DEFAULT_T_IO_SEC)
    t_compute = float(t_compute_sec if t_compute_sec is not None else _DEFAULT_T_COMPUTE_SEC)

    slice_days = resolve_slice_open_days_for_job(
        raw_slice,
        min_required_records=min_records,
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
    system_cap = resolve_system_process_cap()
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
    "build_runtime_plan",
    "ideal_preload_from_timings",
    "is_duckdb_backend",
    "preload_depth_from_memory",
    "resolve_reader_workers",
    "resolve_slice_open_days_for_job",
    "resolve_system_process_cap",
]
