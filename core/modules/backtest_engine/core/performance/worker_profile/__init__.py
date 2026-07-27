"""worker.json → ``job_pipeline`` profile：并行度与 entity_based dispatch 默认值。

配置键名仍为 ``worker.json`` 的 ``job_pipeline``（兼容既有 userspace）；
Python 归属 BE，供 planner / strategy / worker 解析 performance。
"""
from core.modules.backtest_engine.core.performance.worker_profile.constants import (
    CALENDAR_SLICE_RUNTIME_DEFAULTS,
    DEFAULT_PRICE_ENTITIES_PER_JOB,
    DISPATCH_DEFAULTS_BY_PROFILE,
    ENUMERATOR_DISPATCH_DEFAULTS,
    ENUMERATOR_STRATEGY_CALENDAR_SLICE_KEYS,
    ENUMERATOR_STRATEGY_DISPATCH_KEYS,
    JOB_PIPELINE_PROFILE_NAMES,
    PRICE_FACTOR_DISPATCH_DEFAULTS,
    PRICE_STRATEGY_DISPATCH_KEYS,
    SCANNER_DISPATCH_DEFAULTS,
    USER_PIPELINE_POOL_KEYS,
    WorkerProfiles,
)
from core.modules.backtest_engine.core.performance.worker_profile.dispatch_settings import (
    clamp_entities_per_job,
    default_auto_entities_per_job,
    entities_per_job_bounds,
)
from core.modules.backtest_engine.core.performance.worker_profile.resolver import (
    job_pipeline_profile,
    pipeline_max_parallel_jobs_cap,
    pipeline_reserve_cores,
    profile_calendar_slice_config,
    profile_dispatch_config,
    profile_entity_based_performance,
    profile_max_parallel_jobs_cap,
    profile_reserve_cores,
    resolve_entity_based_performance_for_profile,
    resolve_pipeline_workers,
    resolve_worker_profile,
)
from core.modules.backtest_engine.core.schedule.entity_based.probe import WorkerProbe

__all__ = [
    "CALENDAR_SLICE_RUNTIME_DEFAULTS",
    "DEFAULT_PRICE_ENTITIES_PER_JOB",
    "DISPATCH_DEFAULTS_BY_PROFILE",
    "ENUMERATOR_DISPATCH_DEFAULTS",
    "ENUMERATOR_STRATEGY_CALENDAR_SLICE_KEYS",
    "ENUMERATOR_STRATEGY_DISPATCH_KEYS",
    "JOB_PIPELINE_PROFILE_NAMES",
    "PRICE_FACTOR_DISPATCH_DEFAULTS",
    "PRICE_STRATEGY_DISPATCH_KEYS",
    "SCANNER_DISPATCH_DEFAULTS",
    "USER_PIPELINE_POOL_KEYS",
    "WorkerProfiles",
    "WorkerProbe",
    "clamp_entities_per_job",
    "default_auto_entities_per_job",
    "entities_per_job_bounds",
    "job_pipeline_profile",
    "pipeline_max_parallel_jobs_cap",
    "pipeline_reserve_cores",
    "profile_calendar_slice_config",
    "profile_dispatch_config",
    "profile_entity_based_performance",
    "profile_max_parallel_jobs_cap",
    "profile_reserve_cores",
    "resolve_entity_based_performance_for_profile",
    "resolve_pipeline_workers",
    "resolve_worker_profile",
]
