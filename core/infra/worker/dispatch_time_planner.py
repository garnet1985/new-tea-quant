"""按探针测得的 sec/entity 与 job 固定开销规划 worker 数与 entities_per_job。"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any, Dict, Optional

from core.infra.job_pipeline.probe import WorkerProbe

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
) -> TimeDispatchPlan:
    """
    时间探针驱动的 dispatch 规划。

    - ``N*C < O`` → 主进程单 batch（``run_in_main_process=True``）
    - 否则在 ``W ∈ [1, Wmax]`` 上最小化 ``O + ceil(N/W)*C``
    """
    total_entities = max(0, int(total_entities))
    c = max(0.0, float(sec_per_entity))
    o = max(0.0, float(sec_per_job_overhead))

    ep_override = _parse_int_override(performance, "entities_per_job")
    mw_override_raw = performance.get("max_workers")
    mw_explicit = mw_override_raw not in (None, "", "auto")

    wmax = WorkerProbe.resolve(
        "auto",
        reserve_cores=int(performance.get("reserve_cores", 1)),
        cap=int(performance.get("max_workers_cap", DEFAULT_MAX_WORKERS_CAP)),
    )
    if mw_explicit:
        wmax = WorkerProbe.resolve(
            mw_override_raw,
            reserve_cores=int(performance.get("reserve_cores", 1)),
            cap=performance.get("max_workers_cap"),
        )

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

    run_in_main = bool(performance.get("force_main_process", False))
    ep_source = "auto"
    mw_source = "auto"

    if ep_override is not None:
        entities_per_job = ep_override
        ep_source = "settings"
        dispatch_jobs = max(1, math.ceil(total_entities / entities_per_job))
        max_workers = (
            WorkerProbe.resolve(
                mw_override_raw if mw_explicit else dispatch_jobs,
                reserve_cores=int(performance.get("reserve_cores", 1)),
                cap=performance.get("max_workers_cap"),
            )
            if mw_explicit
            else min(wmax, dispatch_jobs)
        )
        mw_source = "settings" if mw_explicit else "auto_from_jobs"
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
        if mw_explicit:
            best_w = min(best_w, wmax)
            best_wall = estimate_dispatch_wall_sec(
                total_entities=total_entities,
                max_workers=best_w,
                sec_per_entity=c,
                sec_per_job_overhead=o,
            )
            mw_source = "settings"
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
