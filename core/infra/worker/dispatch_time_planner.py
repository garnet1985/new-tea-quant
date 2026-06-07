"""按探针测得的 sec/entity 与 job 固定开销规划 worker 数与 entities_per_job。"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any, Dict, Optional

from core.infra.job_pipeline.profile.probe import WorkerProbe
from core.infra.job_pipeline.profile import (
    WorkerProfiles,
    profile_max_parallel_jobs_cap,
    profile_reserve_cores,
)

logger = logging.getLogger(__name__)

DEFAULT_MAX_WORKERS_CAP: int = 4


@dataclass(frozen=True)
class TimeDispatchPlan:
    entities_per_job: int
    max_workers: int
    dispatch_jobs: int
    run_in_main_process: bool
    sec_per_entity: float
    sec_per_job_overhead: float
    estimated_wall_sec: float
    source_entities_per_job: str
    source_max_workers: str


def estimate_dispatch_wall_sec(
    *,
    total_entities: int,
    max_workers: int,
    sec_per_entity: float,
    sec_per_job_overhead: float,
) -> float:
    """T(W) = O + ceil(N/W)*C（W 个 worker 并行，各 job 约 N/W 股）。"""
    n = max(0, int(total_entities))
    if n <= 0:
        return 0.0
    w = max(1, min(int(max_workers), n))
    entities_per_job = max(1, math.ceil(n / w))
    return float(sec_per_job_overhead) + entities_per_job * float(sec_per_entity)


def _parse_int_override(performance: Dict[str, Any], key: str) -> Optional[int]:
    raw = performance.get(key)
    if raw in (None, "", "auto"):
        return None
    return max(1, int(raw))


def resolve_time_dispatch_plan(
    *,
    total_entities: int,
    performance: Dict[str, Any],
    sec_per_entity: float,
    sec_per_job_overhead: float,
    log_label: str = "调度",
    worker_profile: str = WorkerProfiles.PRICE_FACTOR,
) -> TimeDispatchPlan:
    """
    时间探针驱动的 dispatch 规划。

    - ``N*C < O`` → 主进程单 batch（``run_in_main_process=True``）
    - 否则在 ``W ∈ [1, Wmax]`` 上最小化 ``O + ceil(N/W)*C``
    """
    total_entities = max(0, int(total_entities))
    c = max(0.0, float(sec_per_entity))
    o = max(0.0, float(sec_per_job_overhead))

    if total_entities <= 0:
        return TimeDispatchPlan(
            entities_per_job=1,
            max_workers=1,
            dispatch_jobs=0,
            run_in_main_process=True,
            sec_per_entity=c,
            sec_per_job_overhead=o,
            estimated_wall_sec=0.0,
            source_entities_per_job="empty",
            source_max_workers="empty",
        )

    wmax = WorkerProbe.resolve(
        "auto",
        reserve_cores=profile_reserve_cores(worker_profile),
        cap=profile_max_parallel_jobs_cap(worker_profile),
    )

    ep_override = _parse_int_override(performance, "entities_per_job")
    run_in_main = bool(performance.get("force_main_process", False))
    ep_source = "auto"
    mw_source = "profile_auto"

    if ep_override is not None:
        entities_per_job = ep_override
        ep_source = "profile"
        dispatch_jobs = max(1, math.ceil(total_entities / entities_per_job))
        max_workers = min(wmax, dispatch_jobs)
        wall = estimate_dispatch_wall_sec(
            total_entities=total_entities,
            max_workers=max_workers,
            sec_per_entity=c,
            sec_per_job_overhead=o,
        )
    elif run_in_main or (c > 0 and total_entities * c < o):
        entities_per_job = total_entities
        max_workers = 1
        dispatch_jobs = 1
        run_in_main = True
        ep_source = "main_process" if total_entities * c < o else "forced"
        mw_source = "main_process"
        wall = total_entities * c
    else:
        best_w = 1
        best_wall = estimate_dispatch_wall_sec(
            total_entities=total_entities,
            max_workers=1,
            sec_per_entity=c,
            sec_per_job_overhead=o,
        )
        upper = min(wmax, total_entities)
        for w in range(2, upper + 1):
            trial = estimate_dispatch_wall_sec(
                total_entities=total_entities,
                max_workers=w,
                sec_per_entity=c,
                sec_per_job_overhead=o,
            )
            if trial < best_wall:
                best_wall = trial
                best_w = w
        max_workers = best_w
        entities_per_job = max(1, math.ceil(total_entities / max_workers))
        dispatch_jobs = max(1, math.ceil(total_entities / entities_per_job))
        max_workers = min(max_workers, dispatch_jobs)
        wall = best_wall
        run_in_main = False

    plan = TimeDispatchPlan(
        entities_per_job=entities_per_job,
        max_workers=max(1, max_workers),
        dispatch_jobs=dispatch_jobs,
        run_in_main_process=run_in_main,
        sec_per_entity=c,
        sec_per_job_overhead=o,
        estimated_wall_sec=wall,
        source_entities_per_job=ep_source,
        source_max_workers=mw_source,
    )
    logger.info(
        "%s 时间调度: entities=%s, C=%.4fs/股, O=%.3fs, "
        "workers=%s (%s), entities_per_job=%s (%s), jobs≈%s, "
        "main_process=%s, 估 wall=%.2fs",
        log_label,
        total_entities,
        c,
        o,
        plan.max_workers,
        plan.source_max_workers,
        plan.entities_per_job,
        plan.source_entities_per_job,
        plan.dispatch_jobs,
        plan.run_in_main_process,
        plan.estimated_wall_sec,
    )
    return plan


__all__ = [
    "TimeDispatchPlan",
    "estimate_dispatch_wall_sec",
    "resolve_time_dispatch_plan",
    "DEFAULT_MAX_WORKERS_CAP",
]
