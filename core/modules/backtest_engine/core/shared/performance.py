"""Backtest Engine performance settings — base defaults, merge, validate, resolve."""
from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Any, Dict, Optional, Union

from core.infra.machine_capacity import MachineCapacity, MachineInfo

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
    entities_per_job_min: int = 1
    entities_per_job_max: int = 500
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
    slice_probe: Optional[bool] = None
    dispatch_probe: bool = True
    mb_per_slice_staged: Optional[float] = None
    probe_slice_count: int = 2
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
            "slice_probe": self.slice_probe,
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
        if "queue_depth" in settings and "queue_capacity" not in settings:
            settings["queue_capacity"] = settings["queue_depth"]
        if "prefetch_enabled" in settings and "preload_depth" not in settings:
            settings["preload_depth"] = (
                DEFAULT_PRELOAD_DEPTH if settings["prefetch_enabled"] else 1
            )

    @classmethod
    def resolve_for_planning(
        cls,
        performance: RawPerformance,
        capacity: MachineCapacity,
        *,
        dispatch_slices: int,
    ) -> RawPerformance:
        """Resolve ``auto`` fields once before planner / OOM logic."""
        perf = cls.from_dict(performance)
        perf.validate()
        settings = perf.to_dict()
        cls.normalize_worker_fields(settings)

        if _is_auto(settings.get("slice_open_days")):
            settings["slice_open_days"] = DEFAULT_SLICE_OPEN_DAYS

        available_workers = MachineInfo.get_available_workers(capacity)
        if _is_auto(settings.get("reader_workers")):
            settings["reader_workers"] = max(1, available_workers - 1)

        if _is_auto(settings.get("preload_depth")):
            prefetch_enabled = settings.get("prefetch_enabled", True)
            settings["preload_depth"] = DEFAULT_PRELOAD_DEPTH if prefetch_enabled else 1

        preload_depth = int(settings["preload_depth"])
        if _is_auto(settings.get("queue_capacity")):
            reader_workers = int(settings["reader_workers"])
            settings["queue_capacity"] = max(preload_depth * 2, reader_workers)

        if _is_auto(settings.get("compute_processes")):
            settings["compute_processes"] = 1

        cls._validate_resolved(settings)
        if dispatch_slices > 0:
            settings["_dispatch_slices"] = dispatch_slices
        return settings

    @staticmethod
    def _validate_resolved(settings: RawPerformance) -> None:
        slice_open_days = int(settings.get("slice_open_days", 0))
        if slice_open_days <= 0:
            raise ValueError(f"slice_open_days must be > 0: {slice_open_days}")
        for field_name in ("reader_workers", "compute_processes", "queue_capacity", "preload_depth"):
            value = int(settings[field_name])
            if value <= 0:
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
