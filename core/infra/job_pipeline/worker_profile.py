"""JobPipeline 并行度：按 worker profile 读取系统配置（非用户策略 settings）。"""
from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, FrozenSet, Optional

from core.infra.job_pipeline.probe import WorkerProbe

USER_PIPELINE_POOL_KEYS = frozenset(
    {
        "max_workers",
        "max_parallel_jobs_cap",
    }
)

_PROFILE_KEYS: FrozenSet[str] = frozenset(
    {
        "default",
        "enumerator",
        "tag",
        "price_factor",
        "scanner",
    }
)


class WorkerProfiles:
    """``worker.json`` → ``job_pipeline`` 下的 profile 名。"""

    DEFAULT = "default"
    ENUMERATOR = "enumerator"
    TAG = "tag"
    PRICE_FACTOR = "price_factor"
    SCANNER = "scanner"


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
    from core.infra.project_context.config_manager import ConfigManager

    cfg = ConfigManager.load_worker_config()
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
    """
    合并 ``default`` + 指定 worker profile。

    配置来源：``core/default_config/worker.json``，用户可在
    ``userspace/config/worker.json`` 用相同结构覆盖。
    """
    block = _job_pipeline_block()
    default = _default_profile_block(block)
    wid = str(worker_id or WorkerProfiles.DEFAULT).strip() or WorkerProfiles.DEFAULT
    if wid == WorkerProfiles.DEFAULT:
        return default
    specific = block.get(wid)
    if not isinstance(specific, dict):
        specific = {}
    return {**default, **specific}


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
    """按 worker profile 解析 ProcessPool 并行 job 数（始终 auto）。"""
    workers = WorkerProbe.resolve(
        "auto",
        reserve_cores=profile_reserve_cores(worker_id),
        cap=profile_max_parallel_jobs_cap(worker_id),
    )
    if dispatch_jobs is not None and dispatch_jobs > 0:
        workers = min(workers, dispatch_jobs)
    return max(1, workers)


def job_pipeline_profile(worker_id: str = WorkerProfiles.DEFAULT) -> Dict[str, Any]:
    """兼容旧名：返回合并后的 profile dict。"""
    return resolve_worker_profile(worker_id)


def pipeline_reserve_cores() -> int:
    return profile_reserve_cores(WorkerProfiles.DEFAULT)


def pipeline_max_parallel_jobs_cap() -> Optional[int]:
    return profile_max_parallel_jobs_cap(WorkerProfiles.DEFAULT)


__all__ = [
    "USER_PIPELINE_POOL_KEYS",
    "WorkerProfiles",
    "job_pipeline_profile",
    "pipeline_max_parallel_jobs_cap",
    "pipeline_reserve_cores",
    "profile_max_parallel_jobs_cap",
    "profile_reserve_cores",
    "resolve_pipeline_workers",
    "resolve_worker_profile",
]
