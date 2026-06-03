"""
Tag 调度规划：在 CPU / 内存约束下解析 entities_per_job 与 max_workers。

目标：尽量保持 bulk stage 收益，同时限制并发 job 内存，降低 OOM 风险。
"""
from __future__ import annotations

import logging
import math
import multiprocessing as mp
from dataclasses import dataclass
from typing import Any, Dict, Optional

from core.infra.job_dispatcher.probe import WorkerProbe

logger = logging.getLogger(__name__)

# 粗算：pickle 约 50–80KB/股（activity-ratio20），子进程还有 ORM/连接/算子开销 → 默认留余量
DEFAULT_MB_PER_ENTITY: float = 0.25
DEFAULT_ENTITIES_PER_JOB: int = 100
DEFAULT_ENTITIES_PER_JOB_MIN: int = 10
# 全量 benchmark 常用 100；200 需配合更大的 mb_per_entity_staged 或充足内存
DEFAULT_ENTITIES_PER_JOB_MAX: int = 100
DEFAULT_MAIN_RESERVE_MB: float = 512.0
DEFAULT_WORKER_MEMORY_FRACTION: float = 0.65
DEFAULT_PREFETCH_AHEAD: int = 1


@dataclass(frozen=True)
class TagDispatchPlan:
    entities_per_job: int
    max_workers: int
    prefetch_ahead: int
    dispatch_jobs: int
    memory_budget_mb: float
    mb_per_entity: float
    worker_job_budget_mb: float
    source_entities_per_job: str
    source_max_workers: str
    source_mb_per_entity: str = "default"


def _get_available_memory_mb() -> Optional[float]:
    try:
        import psutil

        return float(psutil.virtual_memory().available) / (1024.0 * 1024.0)
    except Exception:
        return None


def _auto_memory_budget_mb(performance: Dict[str, Any]) -> float:
    raw = performance.get("dispatch_memory_budget_mb", "auto")
    if raw not in ("auto", None, ""):
        return max(256.0, float(raw))
    available = _get_available_memory_mb()
    if available is None:
        return 4096.0
    fraction = float(performance.get("worker_memory_fraction", DEFAULT_WORKER_MEMORY_FRACTION))
    reserve = float(performance.get("main_process_reserve_mb", DEFAULT_MAIN_RESERVE_MB))
    budget = available * fraction - reserve
    return max(1024.0, min(budget, 16384.0))


def _parse_entities_per_job_override(performance: Dict[str, Any]) -> Optional[int]:
    raw = performance.get("entities_per_job")
    if raw in (None, "", "auto"):
        return None
    return max(1, int(raw))


def _clamp_entities(n: int, performance: Dict[str, Any]) -> int:
    lo = max(1, int(performance.get("entities_per_job_min", DEFAULT_ENTITIES_PER_JOB_MIN)))
    hi = max(lo, int(performance.get("entities_per_job_max", DEFAULT_ENTITIES_PER_JOB_MAX)))
    return max(lo, min(hi, n))


def resolve_tag_dispatch_plan(
    *,
    total_entities: int,
    performance: Dict[str, Any],
    debug_entities_per_job: Optional[int] = None,
    measured_mb_per_entity: Optional[float] = None,
) -> TagDispatchPlan:
    """
    解析 Tag 一次 run 的分组与进程数。

    - ``entities_per_job``：显式整数 > ``"auto"``（按内存与 max_workers）> 默认 100
    - ``max_workers``：``WorkerProbe``；再用内存收紧（in-flight × 单 job 预算）
    - ``prefetch_ahead``：默认 1（stage_in_worker 下 ready 队列几乎无大 payload）
    """
    total_entities = max(0, int(total_entities))
    ep_override = debug_entities_per_job
    if ep_override is None:
        ep_override = _parse_entities_per_job_override(performance)

    if "mb_per_entity_staged" in performance:
        mb_per_entity = max(0.01, float(performance["mb_per_entity_staged"]))
        mb_source = "settings"
    elif measured_mb_per_entity is not None and measured_mb_per_entity > 0:
        mb_per_entity = max(0.01, float(measured_mb_per_entity))
        mb_source = "probe"
    else:
        mb_per_entity = DEFAULT_MB_PER_ENTITY
        mb_source = "default"
    memory_budget_mb = _auto_memory_budget_mb(performance)

    cpu_workers = WorkerProbe.resolve(
        performance.get("max_workers", "auto"),
        reserve_cores=int(performance.get("reserve_cores", 1)),
        cap=performance.get("max_workers_cap"),
    )

    if ep_override is not None:
        entities_per_job = _clamp_entities(ep_override, performance)
        ep_source = "settings"
    else:
        # 先按 CPU 并行度估 in-flight，再反推每 job 股数
        workers_guess = max(1, cpu_workers)
        per_job_mb = memory_budget_mb / workers_guess
        auto_n = int(per_job_mb / mb_per_entity) if mb_per_entity > 0 else DEFAULT_ENTITIES_PER_JOB
        if auto_n < 1:
            auto_n = DEFAULT_ENTITIES_PER_JOB
        entities_per_job = _clamp_entities(auto_n, performance)
        ep_source = "auto"

    dispatch_jobs = max(1, math.ceil(total_entities / entities_per_job)) if total_entities else 0

    worker_job_budget_mb = entities_per_job * mb_per_entity
    if worker_job_budget_mb <= 0:
        worker_job_budget_mb = 1.0

    memory_workers = max(1, int(memory_budget_mb / worker_job_budget_mb))
    max_workers = max(1, min(cpu_workers, memory_workers))
    mw_source = "auto"
    if performance.get("max_workers") not in (None, "", "auto") and not isinstance(
        performance.get("max_workers"), str
    ):
        mw_source = "settings"
    if max_workers < cpu_workers:
        mw_source = f"{mw_source}+memory_cap"

    prefetch = performance.get("prefetch_ahead")
    if prefetch is None:
        prefetch_ahead = DEFAULT_PREFETCH_AHEAD
    else:
        prefetch_ahead = max(0, int(prefetch))

    plan = TagDispatchPlan(
        entities_per_job=entities_per_job,
        max_workers=max_workers,
        prefetch_ahead=prefetch_ahead,
        dispatch_jobs=dispatch_jobs,
        memory_budget_mb=memory_budget_mb,
        mb_per_entity=mb_per_entity,
        worker_job_budget_mb=worker_job_budget_mb,
        source_entities_per_job=ep_source,
        source_max_workers=mw_source,
        source_mb_per_entity=mb_source,
    )
    logger.info(
        "Tag 调度规划: entities=%s → dispatch_jobs≈%s (entities_per_job=%s, %s), "
        "workers=%s (%s), prefetch=%s, "
        "内存预算=%.0fMB, mb_per_entity=%.3f (%s), 单 job 预算≈%.1fMB",
        total_entities,
        plan.dispatch_jobs,
        plan.entities_per_job,
        plan.source_entities_per_job,
        plan.max_workers,
        plan.source_max_workers,
        plan.prefetch_ahead,
        plan.memory_budget_mb,
        plan.mb_per_entity,
        plan.source_mb_per_entity,
        plan.worker_job_budget_mb,
    )
    if (
        ep_source == "auto"
        and entities_per_job >= int(performance.get("entities_per_job_max", DEFAULT_ENTITIES_PER_JOB_MAX))
    ):
        logger.warning(
            "entities_per_job 已顶到上限 %s（内存估算偏乐观时可减小 entities_per_job_max "
            "或增大 mb_per_entity_staged，见 settings.performance）",
            plan.entities_per_job,
        )
    if plan.entities_per_job <= 20 and total_entities > 200:
        logger.warning(
            "entities_per_job 偏小 (%s)，dispatch 次数多、wall 可能偏高；"
            "可增大 performance.entities_per_job 或调低 mb_per_entity_staged",
            plan.entities_per_job,
        )
    if plan.max_workers < cpu_workers:
        logger.warning(
            "max_workers 已由内存收紧: %s → %s（预算 %.0fMB，单 job≈%.1fMB）",
            cpu_workers,
            plan.max_workers,
            plan.memory_budget_mb,
            plan.worker_job_budget_mb,
        )
    return plan
