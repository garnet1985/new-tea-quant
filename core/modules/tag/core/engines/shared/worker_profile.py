"""Tag BE 性能 profile（``worker.json`` → ``job_pipeline.tag``）。

消费者: TagEntityPipeline, TagSlicePipeline

与 strategy enumerator 同构：``dispatch`` = entity_based，``calendar_slice`` = slice_based。
"""

from __future__ import annotations

from typing import Any, Dict

from core.modules.backtest_engine.core.performance.worker_profile import (
    WorkerProfiles,
    profile_calendar_slice_config,
    profile_entity_based_performance,
    resolve_worker_profile,
)


class TagWorkerProfile:
    """``worker.json`` → ``job_pipeline.tag`` → performance dict。"""

    @classmethod
    def entity_based(cls) -> Dict[str, Any]:
        return profile_entity_based_performance(WorkerProfiles.TAG)

    @classmethod
    def slice_based(cls) -> Dict[str, Any]:
        prof = resolve_worker_profile(WorkerProfiles.TAG)
        merged = dict(profile_calendar_slice_config(WorkerProfiles.TAG))
        for key in ("reserve_cores", "max_parallel_jobs_cap"):
            if key in prof and prof[key] is not None:
                merged[key] = prof[key]
        return merged


__all__ = ["TagWorkerProfile"]
