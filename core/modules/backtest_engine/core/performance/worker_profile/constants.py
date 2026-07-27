"""``worker.json`` → ``job_pipeline`` 默认值，以及策略 settings 中应忽略的调度键。

归属 BE：调度默认值供 entity_based planner / performance.resolve 使用。
配置块名仍为 ``job_pipeline``，与既有 userspace 兼容。
"""
from __future__ import annotations

from typing import Any, Dict, FrozenSet


class WorkerProfiles:
    """``worker.json`` → ``job_pipeline`` 下的 profile 名。"""

    DEFAULT = "default"
    ENUMERATOR = "enumerator"
    TAG = "tag"
    PRICE_FACTOR = "price_factor"
    SCANNER = "scanner"


JOB_PIPELINE_PROFILE_NAMES: FrozenSet[str] = frozenset(
    {
        WorkerProfiles.DEFAULT,
        WorkerProfiles.ENUMERATOR,
        WorkerProfiles.TAG,
        WorkerProfiles.PRICE_FACTOR,
        WorkerProfiles.SCANNER,
    }
)

USER_PIPELINE_POOL_KEYS: FrozenSet[str] = frozenset(
    {
        "max_workers",
        "max_parallel_jobs_cap",
    }
)

DEFAULT_PRICE_ENTITIES_PER_JOB: int = 1000

# entity_based 调度：代码 fallback（运行时以 worker.json job_pipeline 为准，会覆盖此处）
ENUMERATOR_POOL_DEFAULTS: Dict[str, Any] = {
    "reserve_cores": 2,
    "max_workers": "auto",
}

ENUMERATOR_DISPATCH_DEFAULTS: Dict[str, Any] = {
    "memory_budget_mb": "auto",
    "memory_floor_mb": "auto",
    "warmup_batch_size": "auto",
    "min_batch_size": "auto",
    "max_batch_size": "auto",
    "monitor_interval": 5,
    "entities_per_job": "auto",
    "entities_per_job_auto_target": 20,
    "entities_per_job_auto_target_medium": 50,
    "dispatch_probe": True,
    "entities_per_job_min": 20,
    "entities_per_job_max": 100,
    "worker_memory_fraction": 0.85,
    "prefetch_ahead": 1,
}

TAG_DISPATCH_DEFAULTS: Dict[str, Any] = {
    "entities_per_job": "auto",
    "dispatch_probe": True,
    "entities_per_job_min": 1,
    "entities_per_job_max": 500,
    "memory_floor_mb": "auto",
}

CALENDAR_SLICE_RUNTIME_DEFAULTS: Dict[str, Any] = {
    "reader_workers": "auto",
    "queue_depth": "auto",
    "prefetch_enabled": True,
}

PRICE_FACTOR_DISPATCH_DEFAULTS: Dict[str, Any] = {
    "entities_per_job": DEFAULT_PRICE_ENTITIES_PER_JOB,
    "dispatch_probe": False,
    "force_main_process": False,
}

# scanner：与 enumerator 同风格由 BE 切 bundle；默认 auto + probe
SCANNER_DISPATCH_DEFAULTS: Dict[str, Any] = {
    "memory_budget_mb": "auto",
    "memory_floor_mb": "auto",
    "warmup_batch_size": "auto",
    "min_batch_size": "auto",
    "max_batch_size": "auto",
    "monitor_interval": 5,
    "entities_per_job": "auto",
    "entities_per_job_auto_target": 50,
    "entities_per_job_auto_target_medium": 100,
    "dispatch_probe": True,
    "entities_per_job_min": 20,
    "entities_per_job_max": 200,
    "worker_memory_fraction": 0.85,
    "prefetch_ahead": 1,
}

DISPATCH_DEFAULTS_BY_PROFILE: Dict[str, Dict[str, Any]] = {
    WorkerProfiles.ENUMERATOR: ENUMERATOR_DISPATCH_DEFAULTS,
    WorkerProfiles.TAG: TAG_DISPATCH_DEFAULTS,
    WorkerProfiles.PRICE_FACTOR: PRICE_FACTOR_DISPATCH_DEFAULTS,
    WorkerProfiles.SCANNER: SCANNER_DISPATCH_DEFAULTS,
}

PROFILE_POOL_DEFAULTS_BY_WORKER: Dict[str, Dict[str, Any]] = {
    WorkerProfiles.DEFAULT: {"reserve_cores": 1, "max_parallel_jobs_cap": None},
    WorkerProfiles.ENUMERATOR: dict(ENUMERATOR_POOL_DEFAULTS),
    WorkerProfiles.TAG: {"reserve_cores": 1, "max_parallel_jobs_cap": None},
    WorkerProfiles.PRICE_FACTOR: {"reserve_cores": 1, "max_parallel_jobs_cap": None},
    WorkerProfiles.SCANNER: {"reserve_cores": 1, "max_parallel_jobs_cap": None},
}

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

ENUMERATOR_STRATEGY_CALENDAR_SLICE_KEYS: FrozenSet[str] = frozenset(
    {"calendar_slice"}
)

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
