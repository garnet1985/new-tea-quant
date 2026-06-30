"""Strategy settings keys owned by worker.json (not user strategy settings)."""
from __future__ import annotations

from typing import Any, Dict, FrozenSet

USER_PIPELINE_POOL_KEYS: FrozenSet[str] = frozenset(
    {
        "max_workers",
        "max_parallel_jobs_cap",
    }
)

DEFAULT_PRICE_ENTITIES_PER_JOB: int = 1000

ENUMERATOR_STRATEGY_DISPATCH_KEYS: FrozenSet[str] = frozenset(
    {
        "memory_budget_mb",
        "memory_floor_mb",
        "main_process_reserve_mb",
        "warmup_batch_size",
        "min_batch_size",
        "max_batch_size",
        "monitor_interval",
        "entities_per_job",
        "entities_per_job_min",
        "entities_per_job_max",
        "dispatch_probe",
        "dispatch_probe_entities",
        "dispatch_probe_safety_factor",
        "mb_per_entity_staged",
        "worker_memory_fraction",
        "prefetch_ahead",
    }
)

ENUMERATOR_STRATEGY_CALENDAR_SLICE_KEYS: FrozenSet[str] = frozenset({"calendar_slice"})

PRICE_STRATEGY_DISPATCH_KEYS: FrozenSet[str] = frozenset(
    {
        "entities_per_job",
        "dispatch_probe",
        "dispatch_probe_entities",
        "dispatch_probe_safety_factor",
        "sec_per_entity_staged",
        "sec_per_job_overhead_staged",
        "force_main_process",
    }
)

STRATEGY_ENUM_EXECUTOR_KEY = "strategy.enum"

__all__ = [
    "DEFAULT_PRICE_ENTITIES_PER_JOB",
    "ENUMERATOR_STRATEGY_CALENDAR_SLICE_KEYS",
    "ENUMERATOR_STRATEGY_DISPATCH_KEYS",
    "PRICE_STRATEGY_DISPATCH_KEYS",
    "STRATEGY_ENUM_EXECUTOR_KEY",
    "USER_PIPELINE_POOL_KEYS",
]
