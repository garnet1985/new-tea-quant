"""Slice memory / width / queue planning (SOT: docs/SLICE_BASED_ALGORITHM.md).

All algorithm entry points are classmethods on ``SliceMemoryPlanner``.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


class SliceWidthError(ValueError):
    """Slice plan cannot be resolved without OOM / readiness risk."""


@dataclass(frozen=True)
class SliceMemoryPlan:
    """Resolved width + in-flight shape for slice_based."""

    slice_open_days: int
    queue_depth: int
    reader_workers: int
    compute_slices: int
    in_flight: int
    mb_per_open_day: float
    min_required: int
    budget_mb: float


class SliceMemoryPlanner:
    """Plan formal slice width and queue under peak in-flight memory.

    ``in_flight = compute_slices + queue_depth + reader_workers`` (peak upper bound).
    """

    SAFETY = 0.8
    COMPUTE_SLICES = 2
    DEFAULT_MIN_REQUIRED = 20
    COMPUTE_PROCESSES = 1

    @classmethod
    def default_min_required(cls, min_required: Optional[int]) -> int:
        raw = 0 if min_required is None else int(min_required)
        return cls.DEFAULT_MIN_REQUIRED if raw <= 0 else max(1, raw)

    @classmethod
    def reader_workers_from_cpu(cls, *, cpu_count: int, reserve_cores: int) -> int:
        """R = max(0, cores - reserved - 1 compute process)."""
        return max(0, int(cpu_count) - max(0, int(reserve_cores)) - cls.COMPUTE_PROCESSES)

    @classmethod
    def in_flight(cls, *, queue_depth: int, reader_workers: int) -> int:
        return cls.COMPUTE_SLICES + max(0, int(queue_depth)) + max(0, int(reader_workers))

    @classmethod
    def assert_probe_fits(cls, *, budget_mb: float, probe_mb: float) -> None:
        """Fail if even 2 probe-sized slices cannot fit under discounted budget."""
        budget = max(float(budget_mb), 0.0)
        probe = max(float(probe_mb), 0.0)
        if budget * cls.SAFETY < cls.COMPUTE_SLICES * probe:
            raise SliceWidthError(
                f"探针块无法满足回溯双片并存："
                f"budget({budget:.1f})*{cls.SAFETY} < "
                f"{cls.COMPUTE_SLICES}*{probe:.1f}MB；将 OOM，请减小 min_required 或增加内存"
            )

    @classmethod
    def resolve_initial(
        cls,
        *,
        budget_mb: float,
        probe_mb: float,
        probe_width: int,
        cpu_count: int,
        reserve_cores: int = 1,
        min_required: Optional[int] = None,
    ) -> SliceMemoryPlan:
        """Initial plan: probe supplies MB only; N from memory feasibility, not timing ratio."""
        need = cls.default_min_required(min_required)
        width_probe = max(1, int(probe_width))
        cls.assert_probe_fits(budget_mb=budget_mb, probe_mb=probe_mb)

        mb_per_point = max(float(probe_mb), 1e-6) / float(width_probe)
        readers = cls.reader_workers_from_cpu(
            cpu_count=cpu_count, reserve_cores=reserve_cores
        )
        budget = max(float(budget_mb), 0.0)
        usable = budget * cls.SAFETY

        for queue in range(readers, -1, -1):
            flight = cls.in_flight(queue_depth=queue, reader_workers=readers)
            width = int(math.floor(usable / float(flight) / mb_per_point))
            if width >= need:
                return SliceMemoryPlan(
                    slice_open_days=width,
                    queue_depth=queue,
                    reader_workers=readers,
                    compute_slices=cls.COMPUTE_SLICES,
                    in_flight=flight,
                    mb_per_open_day=mb_per_point,
                    min_required=need,
                    budget_mb=budget,
                )

        raise SliceWidthError(
            f"内存不足以支撑 min_required={need}："
            f"即使 queue=0、readers={readers}，"
            f"in_flight={cls.in_flight(queue_depth=0, reader_workers=readers)} "
            f"下片宽仍 < min_required "
            f"(budget={budget:.1f}MB, mb_per_open_day={mb_per_point:.4f})"
        )

    @classmethod
    def refine_queue_depth(
        cls,
        *,
        budget_mb: float,
        mb_per_slice: float,
        reader_workers: int,
        current_queue: int,
        t_load_sec: Optional[float] = None,
        t_compute_sec: Optional[float] = None,
    ) -> int:
        """Runtime N: prefer ceil(t_load/t_compute), clamped by memory at fixed width."""
        readers = max(0, int(reader_workers))
        per = max(float(mb_per_slice), 1e-6)
        usable = max(float(budget_mb), 0.0) * cls.SAFETY
        n_max = int(math.floor(usable / per - cls.COMPUTE_SLICES - readers))
        n_max = max(0, n_max)

        if t_load_sec is not None and t_compute_sec is not None:
            load = max(float(t_load_sec), 0.0)
            compute = max(float(t_compute_sec), 1e-9)
            n_ideal = int(math.ceil(load / compute))
            return max(0, min(n_max, n_ideal))

        return max(0, min(n_max, int(current_queue)))

    @classmethod
    def resolve_from_unit_cost(
        cls,
        *,
        budget_mb: float,
        mb_per_open_day: float,
        cpu_count: int,
        reserve_cores: int = 1,
        min_required: Optional[int] = None,
    ) -> SliceMemoryPlan:
        """Same as ``resolve_initial`` when probe_mb = mb_per_open_day * min_required."""
        need = cls.default_min_required(min_required)
        per = max(float(mb_per_open_day), 1e-6)
        probe_mb = per * float(need)
        return cls.resolve_initial(
            budget_mb=budget_mb,
            probe_mb=probe_mb,
            probe_width=need,
            cpu_count=cpu_count,
            reserve_cores=reserve_cores,
            min_required=need,
        )


__all__ = [
    "SliceMemoryPlan",
    "SliceMemoryPlanner",
    "SliceWidthError",
]
