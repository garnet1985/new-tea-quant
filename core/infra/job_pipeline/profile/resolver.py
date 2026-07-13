"""从 worker.json job_pipeline profile 解析并行度与 dispatch 配置。"""
from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, Optional

from core.infra.project_context import ProjectContext
from core.infra.job_pipeline.profile.constants import (
    DISPATCH_DEFAULTS_BY_PROFILE,
    PROFILE_POOL_DEFAULTS_BY_WORKER,
    WorkerProfiles,
)
from core.infra.job_pipeline.profile.probe import WorkerProbe


def _parse_reserve_cores(raw: Any, *, fallback: int = 1) -> int:
    try:
        return max(0, int(raw))
    except (TypeError, ValueError):
        return fallback


def _parse_max_parallel_jobs_cap(raw: Any) -> Optional[int]:
    if raw in (None, "", "null"):
        return None
    try:
        return max(1, int(raw))
    except (TypeError, ValueError):
        return None


@lru_cache(maxsize=1)
def _job_pipeline_block() -> Dict[str, Any]:
    cfg = ProjectContext.config.load_core_config("worker", )
    block = cfg.get("job_pipeline") or {}
    return block if isinstance(block, dict) else {}


def _default_profile_block(block: Dict[str, Any]) -> Dict[str, Any]:
    nested = block.get(WorkerProfiles.DEFAULT)
    if isinstance(nested, dict):
        return dict(nested)
    flat = {
        key: block[key]
        for key in ("reserve_cores", "max_parallel_jobs_cap")
        if key in block
    }
    return flat


def resolve_worker_profile(worker_id: str = WorkerProfiles.DEFAULT) -> Dict[str, Any]:
    block = _job_pipeline_block()
    default = _default_profile_block(block)
    wid = str(worker_id or WorkerProfiles.DEFAULT).strip() or WorkerProfiles.DEFAULT
    if wid == WorkerProfiles.DEFAULT:
        return default
    pool_defaults = dict(PROFILE_POOL_DEFAULTS_BY_WORKER.get(wid, {}))
    specific = block.get(wid)
    if not isinstance(specific, dict):
        specific = {}
    return {**default, **pool_defaults, **specific}


def profile_calendar_slice_config(worker_id: str = WorkerProfiles.ENUMERATOR) -> Dict[str, Any]:
    from core.infra.job_pipeline.profile.constants import CALENDAR_SLICE_RUNTIME_DEFAULTS

    defaults = dict(CALENDAR_SLICE_RUNTIME_DEFAULTS)
    prof = resolve_worker_profile(worker_id)
    block = prof.get("calendar_slice")
    if isinstance(block, dict):
        return {**defaults, **block}
    return defaults


def profile_dispatch_config(worker_id: str) -> Dict[str, Any]:
    defaults = dict(DISPATCH_DEFAULTS_BY_PROFILE.get(worker_id, {}))
    prof = resolve_worker_profile(worker_id)
    dispatch = prof.get("dispatch")
    if isinstance(dispatch, dict):
        return {**defaults, **dispatch}
    return defaults


def profile_reserve_cores(worker_id: str = WorkerProfiles.DEFAULT) -> int:
    prof = resolve_worker_profile(worker_id)
    return _parse_reserve_cores(prof.get("reserve_cores", 1))


def profile_max_parallel_jobs_cap(worker_id: str = WorkerProfiles.DEFAULT) -> Optional[int]:
    prof = resolve_worker_profile(worker_id)
    return _parse_max_parallel_jobs_cap(prof.get("max_parallel_jobs_cap"))


def resolve_pipeline_workers(
    *,
    worker_id: str = WorkerProfiles.DEFAULT,
    dispatch_jobs: Optional[int] = None,
) -> int:
    workers = WorkerProbe.resolve(
        "auto",
        reserve_cores=profile_reserve_cores(worker_id),
        cap=profile_max_parallel_jobs_cap(worker_id),
    )
    if dispatch_jobs is not None and dispatch_jobs > 0:
        workers = min(workers, dispatch_jobs)
    return max(1, workers)


def profile_entity_based_performance(
    worker_id: str = WorkerProfiles.ENUMERATOR,
    override: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """合并 worker profile + dispatch 块，供 entity_based BacktestEngine 使用。"""
    prof = resolve_worker_profile(worker_id)
    dispatch = profile_dispatch_config(worker_id)
    merged: Dict[str, Any] = dict(dispatch)
    for key in ("reserve_cores", "max_parallel_jobs_cap", "max_workers"):
        if key in prof and prof[key] is not None:
            merged[key] = prof[key]
    if override:
        for key, value in override.items():
            if value is not None:
                merged[key] = value
    return merged


def resolve_entity_based_performance_for_profile(
    worker_id: str = WorkerProfiles.ENUMERATOR,
    override: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """profile 合并 + EntityBasedPerformance 校验（enum / tag 等统一入口）。"""
    from core.modules.backtest_engine.core.shared.performance import (
        resolve_entity_based_performance,
    )

    return resolve_entity_based_performance(
        profile_entity_based_performance(worker_id, override)
    )


def job_pipeline_profile(worker_id: str = WorkerProfiles.DEFAULT) -> Dict[str, Any]:
    return resolve_worker_profile(worker_id)


def pipeline_reserve_cores() -> int:
    return profile_reserve_cores(WorkerProfiles.DEFAULT)


def pipeline_max_parallel_jobs_cap() -> Optional[int]:
    return profile_max_parallel_jobs_cap(WorkerProfiles.DEFAULT)
