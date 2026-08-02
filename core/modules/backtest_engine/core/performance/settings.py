"""Backtest Engine performance settings — base defaults, merge, validate, resolve."""
from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Any, Dict, Optional, Union

from core.modules.backtest_engine.core.performance.worker_profile.constants import (
    ENUMERATOR_DISPATCH_DEFAULTS,
)
from core.infra.machine_capacity import MachineInfo
from core.infra.machine_capacity.contracts import MachineCapacity

AutoValue = Union[int, float, str, bool, None]
RawPerformance = Dict[str, Any]

DEFAULT_SLICE_OPEN_DAYS = 20
DEFAULT_PRELOAD_DEPTH = 2


def _is_auto(value: Any) -> bool:
    return value in (None, "", "auto")


def _as_int(value: Any, *, field_name: str) -> int:
    if _is_auto(value):
        raise ValueError(f"{field_name} must be resolved before int coercion")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be int-like: {value!r}") from exc


def _merge_known_fields(base: Dict[str, Any], override: Optional[RawPerformance]) -> Dict[str, Any]:
    merged = dict(base)
    if override:
        for key, value in override.items():
            if value is not None:
                merged[key] = value
    return merged


@dataclass
class EntityBasedPerformance:
    """entity_based dispatch settings (engine base + caller override)."""

    max_workers: Union[int, str] = "auto"
    entities_per_job: Union[int, str] = "auto"
    dispatch_probe: bool = True
    prefetch_ahead: int = 1
    reserve_cores: int = 1
    max_parallel_jobs_cap: Optional[int] = None
    entities_per_job_min: int = ENUMERATOR_DISPATCH_DEFAULTS["entities_per_job_min"]
    entities_per_job_max: int = ENUMERATOR_DISPATCH_DEFAULTS["entities_per_job_max"]
    memory_budget_mb: Union[int, float, str] = "auto"
    memory_floor_mb: Union[int, float, str] = "auto"
    worker_memory_fraction: float = 0.85
    force_main_process: bool = False
    mb_per_entity_staged: Optional[float] = None
    dispatch_probe_safety_factor: float = 1.0
    duckdb_process_pool_scope: str = "auto"
    duckdb_resume_main_after_pool: bool = True
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def base(cls) -> EntityBasedPerformance:
        return cls()

    @classmethod
    def from_dict(cls, data: Optional[RawPerformance]) -> EntityBasedPerformance:
        raw = dict(data or {})
        known = {f.name for f in fields(cls) if f.name != "extra"}
        kwargs = {key: raw.pop(key) for key in list(raw) if key in known}
        perf = cls(**kwargs)
        perf.extra = raw
        return perf

    def merge(self, override: Optional[RawPerformance]) -> EntityBasedPerformance:
        merged = _merge_known_fields(self.to_dict(), override)
        return EntityBasedPerformance.from_dict(merged)

    def validate(self) -> None:
        if self.prefetch_ahead < 0:
            raise ValueError(f"prefetch_ahead must be >= 0: {self.prefetch_ahead}")
        if self.reserve_cores < 0:
            raise ValueError(f"reserve_cores must be >= 0: {self.reserve_cores}")
        if self.entities_per_job_min <= 0 or self.entities_per_job_max <= 0:
            raise ValueError("entities_per_job_min/max must be > 0")
        if self.entities_per_job_min > self.entities_per_job_max:
            raise ValueError("entities_per_job_min must be <= entities_per_job_max")
        if not _is_auto(self.max_workers) and int(self.max_workers) <= 0:
            raise ValueError(f"max_workers must be > 0: {self.max_workers}")
        if not _is_auto(self.entities_per_job) and int(self.entities_per_job) <= 0:
            raise ValueError(f"entities_per_job must be > 0: {self.entities_per_job}")

    def to_dict(self) -> RawPerformance:
        out: RawPerformance = {
            "max_workers": self.max_workers,
            "entities_per_job": self.entities_per_job,
            "dispatch_probe": self.dispatch_probe,
            "prefetch_ahead": self.prefetch_ahead,
            "reserve_cores": self.reserve_cores,
            "max_parallel_jobs_cap": self.max_parallel_jobs_cap,
            "entities_per_job_min": self.entities_per_job_min,
            "entities_per_job_max": self.entities_per_job_max,
            "memory_budget_mb": self.memory_budget_mb,
            "memory_floor_mb": self.memory_floor_mb,
            "worker_memory_fraction": self.worker_memory_fraction,
            "force_main_process": self.force_main_process,
            "mb_per_entity_staged": self.mb_per_entity_staged,
            "dispatch_probe_safety_factor": self.dispatch_probe_safety_factor,
            "duckdb_process_pool_scope": self.duckdb_process_pool_scope,
            "duckdb_resume_main_after_pool": self.duckdb_resume_main_after_pool,
        }
        out.update(self.extra)
        return out


@dataclass
class SliceBasedPerformance:
    """slice_based dispatch settings (engine base + caller override)."""

    reader_workers: Union[int, str] = "auto"
    queue_depth: Union[int, str] = "auto"
    queue_capacity: Union[int, str] = "auto"
    prefetch_enabled: bool = True
    preload_depth: Union[int, str] = "auto"
    slice_open_days: Union[int, str] = "auto"
    compute_processes: Union[int, str] = 1
    reserve_cores: int = 1
    max_parallel_jobs_cap: Optional[int] = None
    # Canonical on/off for dispatch probe (same name as entity_based).
    # Incoming ``slice_probe`` is folded into this in ``from_dict``.
    dispatch_probe: bool = True
    mb_per_slice_staged: Optional[float] = None
    # Head-phase length (formal slices that count toward output).
    probe_slice_count: int = 2
    # Deprecated / ignored for slice sizing (kept for config back-compat only):
    # slice width follows ``slice_open_days``; entities are never truncated.
    probe_slice_open_days: int = 5
    probe_entity_count: int = 2
    slice_probe_safety_factor: Optional[float] = None
    dispatch_probe_safety_factor: float = 1.0
    duckdb_process_pool_scope: str = "auto"
    duckdb_resume_main_after_pool: bool = True
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def base(cls) -> SliceBasedPerformance:
        return cls()

    @classmethod
    def from_dict(cls, data: Optional[RawPerformance]) -> SliceBasedPerformance:
        raw = dict(data or {})
        # Deprecated alias → canonical dispatch_probe (alias wins when present).
        if "slice_probe" in raw:
            alias = raw.pop("slice_probe")
            if alias is not None:
                raw["dispatch_probe"] = bool(alias)
        known = {f.name for f in fields(cls) if f.name != "extra"}
        kwargs = {key: raw.pop(key) for key in list(raw) if key in known}
        perf = cls(**kwargs)
        perf.extra = raw
        return perf

    def merge(self, override: Optional[RawPerformance]) -> SliceBasedPerformance:
        merged = _merge_known_fields(self.to_dict(), override)
        return SliceBasedPerformance.from_dict(merged)

    def validate(self) -> None:
        if self.reserve_cores < 0:
            raise ValueError(f"reserve_cores must be >= 0: {self.reserve_cores}")
        for name in ("reader_workers", "compute_processes", "queue_capacity", "preload_depth", "slice_open_days"):
            value = getattr(self, name)
            if not _is_auto(value) and _as_int(value, field_name=name) <= 0:
                raise ValueError(f"{name} must be > 0: {value}")

    def to_dict(self) -> RawPerformance:
        out: RawPerformance = {
            "reader_workers": self.reader_workers,
            "queue_depth": self.queue_depth,
            "queue_capacity": self.queue_capacity,
            "prefetch_enabled": self.prefetch_enabled,
            "preload_depth": self.preload_depth,
            "slice_open_days": self.slice_open_days,
            "compute_processes": self.compute_processes,
            "reserve_cores": self.reserve_cores,
            "max_parallel_jobs_cap": self.max_parallel_jobs_cap,
            "dispatch_probe": self.dispatch_probe,
            "mb_per_slice_staged": self.mb_per_slice_staged,
            "probe_slice_count": self.probe_slice_count,
            "probe_slice_open_days": self.probe_slice_open_days,
            "probe_entity_count": self.probe_entity_count,
            "slice_probe_safety_factor": self.slice_probe_safety_factor,
            "dispatch_probe_safety_factor": self.dispatch_probe_safety_factor,
            "duckdb_process_pool_scope": self.duckdb_process_pool_scope,
            "duckdb_resume_main_after_pool": self.duckdb_resume_main_after_pool,
        }
        out.update(self.extra)
        return out

    @staticmethod
    def normalize_worker_fields(settings: RawPerformance) -> None:
        """Canonical depth name is ``preload_depth``.

        ``queue_depth`` / ``queue_capacity`` are legacy aliases. If only an
        alias is set, lift it into ``preload_depth``. At plan time
        ``queue_capacity`` is forced equal to ``preload_depth``.

        Probe switch: canonical ``dispatch_probe`` (see ``from_dict`` for
        deprecated ``slice_probe`` alias).
        """
        if _is_auto(settings.get("preload_depth")):
            alias = settings.get("queue_capacity")
            if _is_auto(alias):
                alias = settings.get("queue_depth")
            if not _is_auto(alias):
                settings["preload_depth"] = alias
        if settings.get("prefetch_enabled") is False and _is_auto(
            settings.get("preload_depth")
        ):
            settings["preload_depth"] = 1

    @classmethod
    def resolve_for_planning(
        cls,
        performance: RawPerformance,
        capacity: MachineCapacity,
        *,
        dispatch_slices: int,
    ) -> RawPerformance:
        """Resolve known fields before planner.

        - ``reader_workers`` auto → full standby pool (``cpu - reserve_cores``)
        - ``preload_depth`` stays ``auto`` until probe timings + memory clip
        - ``queue_capacity`` tracks ``preload_depth`` after planner resolves it
        """
        perf = cls.from_dict(performance)
        perf.validate()
        settings = perf.to_dict()
        cls.normalize_worker_fields(settings)

        if _is_auto(settings.get("slice_open_days")):
            settings["slice_open_days"] = DEFAULT_SLICE_OPEN_DAYS

        available_workers = MachineInfo.get_available_workers(capacity)
        if _is_auto(settings.get("reader_workers")):
            # Standby pool: who-is-free reads. Depth (not reader count) matches IO.
            settings["reader_workers"] = max(1, available_workers)
            settings["_reader_workers_fixed"] = True

        if _is_auto(settings.get("compute_processes")):
            settings["compute_processes"] = 1

        # Keep preload_depth / queue_capacity as auto until SlicePlanner uses probe.
        if not _is_auto(settings.get("preload_depth")):
            depth = max(1, int(settings["preload_depth"]))
            settings["preload_depth"] = depth
            settings["queue_capacity"] = depth
            settings["queue_depth"] = depth

        # Strip deprecated probe truncation knobs so they cannot affect sizing.
        settings.pop("probe_slice_open_days", None)
        settings.pop("probe_entity_count", None)

        cls._validate_resolved(settings)
        if dispatch_slices > 0:
            settings["_dispatch_slices"] = dispatch_slices
        return settings

    @staticmethod
    def _validate_resolved(settings: RawPerformance) -> None:
        slice_open_days = int(settings.get("slice_open_days", 0))
        if slice_open_days <= 0:
            raise ValueError(f"slice_open_days must be > 0: {slice_open_days}")
        for field_name in ("reader_workers", "compute_processes"):
            value = int(settings[field_name])
            if value <= 0:
                raise ValueError(f"{field_name} must be > 0: {value}")
        for field_name in ("preload_depth", "queue_capacity"):
            value = settings.get(field_name)
            if _is_auto(value):
                continue
            if int(value) <= 0:
                raise ValueError(f"{field_name} must be > 0: {value}")


def resolve_entity_based_performance(
    override: Optional[RawPerformance] = None,
) -> RawPerformance:
    perf = EntityBasedPerformance.base().merge(override)
    perf.validate()
    return perf.to_dict()


def resolve_slice_based_performance(
    override: Optional[RawPerformance] = None,
) -> RawPerformance:
    perf = SliceBasedPerformance.base().merge(override)
    perf.validate()
    return perf.to_dict()


__all__ = [
    "EntityBasedPerformance",
    "SliceBasedPerformance",
    "resolve_entity_based_performance",
    "resolve_slice_based_performance",
    "DEFAULT_SLICE_OPEN_DAYS",
    "DEFAULT_PRELOAD_DEPTH",
]
