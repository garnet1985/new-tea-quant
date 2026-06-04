"""
进程池调度规划：在 CPU / 内存约束下解析 entities_per_job 与 max_workers。

``auto`` 依赖：
1. 调度探针给出的 ``measured_mb_per_entity``（推荐），或
2. settings 中的 ``mb_per_entity_staged``。

内存预算：可用内存减去 ``memory_floor_mb``（系统保底空闲），再乘 ``worker_memory_fraction``。
不再默认为主进程预留固定 512MB。
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from core.infra.job_pipeline.probe import WorkerProbe

logger = logging.getLogger(__name__)

DEFAULT_WORKER_MEMORY_FRACTION: float = 0.85
DEFAULT_PREFETCH_AHEAD: int = 1
# psutil 不可用时的最后兜底（应在 settings 中显式配置 memory_floor_mb）
_FALLBACK_MEMORY_FLOOR_MB: float = 2048.0
_FALLBACK_BUDGET_MB: float = 4096.0


@dataclass(frozen=True)
class DispatchPlan:
    entities_per_job: int
    max_workers: int
    prefetch_ahead: int
    dispatch_jobs: int
    memory_budget_mb: float
    memory_floor_mb: float
    mb_per_entity: float
    worker_job_budget_mb: float
    source_entities_per_job: str
    source_max_workers: str
    source_mb_per_entity: str = "probe"


def _get_virtual_memory_mb() -> Tuple[Optional[float], Optional[float]]:
    try:
        import psutil

        vm = psutil.virtual_memory()
        total = float(vm.total) / (1024.0 * 1024.0)
        available = float(vm.available) / (1024.0 * 1024.0)
        return total, available
    except Exception:
        return None, None


def resolve_memory_floor_mb(performance: Dict[str, Any]) -> float:
    """
    机器上必须保留的空闲内存（保底），不参与 worker 预算。

    ``memory_floor_mb``：显式 MB；``"auto"``：约 15% 总内存，且不少于 1GB。
    已废弃的 ``main_process_reserve_mb`` 若存在则并入 floor（取较大值）。
    """
    raw = performance.get("memory_floor_mb")
    if raw not in (None, "", "auto"):
        floor = max(0.0, float(raw))
    else:
        total_mb, available_mb = _get_virtual_memory_mb()
        if total_mb is None or available_mb is None:
            floor = _FALLBACK_MEMORY_FLOOR_MB
        else:
            pct = max(1024.0, total_mb * 0.15)
            floor = min(pct, max(1024.0, available_mb * 0.5))

    legacy = performance.get("main_process_reserve_mb")
    if legacy not in (None, ""):
        floor = max(floor, max(0.0, float(legacy)))
    return floor


def resolve_memory_budget_mb(performance: Dict[str, Any]) -> Tuple[float, float]:
    """返回 (worker 可用预算 MB, memory_floor_mb)。"""
    floor_mb = resolve_memory_floor_mb(performance)
    raw = performance.get("dispatch_memory_budget_mb") or performance.get(
        "memory_budget_mb"
    )
    if raw not in ("auto", None, ""):
        return max(256.0, float(raw)), floor_mb

    _total_mb, available_mb = _get_virtual_memory_mb()
    if available_mb is None:
        return _FALLBACK_BUDGET_MB, floor_mb

    usable = max(0.0, available_mb - floor_mb)
    fraction = float(
        performance.get("worker_memory_fraction", DEFAULT_WORKER_MEMORY_FRACTION)
    )
    fraction = max(0.1, min(1.0, fraction))
    budget = usable * fraction
    return max(256.0, min(budget, 16384.0)), floor_mb


def _parse_entities_per_job_override(performance: Dict[str, Any]) -> Optional[int]:
    raw = performance.get("entities_per_job")
    if raw in (None, "", "auto"):
        return None
    return max(1, int(raw))


def _clamp_entities(n: int, performance: Dict[str, Any]) -> int:
    lo = max(1, int(performance.get("entities_per_job_min", 1)))
    hi = max(lo, int(performance.get("entities_per_job_max", 500)))
    return max(lo, min(hi, n))


def _resolve_mb_per_entity(
    performance: Dict[str, Any],
    *,
    measured_mb_per_entity: Optional[float],
    log_label: str,
) -> tuple[float, str]:
    staged = performance.get("mb_per_entity_staged")
    if staged not in (None, ""):
        return max(0.01, float(staged)), "settings"
    if measured_mb_per_entity is not None and measured_mb_per_entity > 0:
        return max(0.01, float(measured_mb_per_entity)), "probe"
    raise ValueError(
        f"{log_label}: entities_per_job=auto 需要调度探针或 settings 中的 "
        "mb_per_entity_staged；请开启 dispatch_probe（默认 true）或手写 mb_per_entity_staged"
    )


def resolve_dispatch_plan(
    *,
    total_entities: int,
    performance: Dict[str, Any],
    log_label: str = "调度",
    debug_entities_per_job: Optional[int] = None,
    measured_mb_per_entity: Optional[float] = None,
) -> DispatchPlan:
    """
    解析一次 run 的分组与进程数。

    - ``entities_per_job``：显式整数 > ``"auto"``（内存 × CPU 推导）
    - ``max_workers``：``WorkerProbe``，再按 in-flight 内存收紧
    """
    total_entities = max(0, int(total_entities))
    ep_override = debug_entities_per_job
    if ep_override is None:
        ep_override = _parse_entities_per_job_override(performance)

    mb_per_entity, mb_source = _resolve_mb_per_entity(
        performance,
        measured_mb_per_entity=measured_mb_per_entity,
        log_label=log_label,
    )
    memory_budget_mb, memory_floor_mb = resolve_memory_budget_mb(performance)

    cpu_workers = WorkerProbe.resolve(
        performance.get("max_workers", "auto"),
        reserve_cores=int(performance.get("reserve_cores", 1)),
        cap=performance.get("max_workers_cap"),
    )

    if ep_override is not None:
        entities_per_job = _clamp_entities(ep_override, performance)
        ep_source = "settings"
    else:
        workers_guess = max(1, cpu_workers)
        per_job_mb = memory_budget_mb / workers_guess
        auto_n = int(per_job_mb / mb_per_entity) if mb_per_entity > 0 else 1
        if auto_n < 1:
            auto_n = 1
        entities_per_job = _clamp_entities(auto_n, performance)
        ep_source = "auto"

    dispatch_jobs = (
        max(1, math.ceil(total_entities / entities_per_job)) if total_entities else 0
    )

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

    plan = DispatchPlan(
        entities_per_job=entities_per_job,
        max_workers=max_workers,
        prefetch_ahead=prefetch_ahead,
        dispatch_jobs=dispatch_jobs,
        memory_budget_mb=memory_budget_mb,
        memory_floor_mb=memory_floor_mb,
        mb_per_entity=mb_per_entity,
        worker_job_budget_mb=worker_job_budget_mb,
        source_entities_per_job=ep_source,
        source_max_workers=mw_source,
        source_mb_per_entity=mb_source,
    )
    ep_max = int(performance.get("entities_per_job_max", 500))
    logger.info(
        "%s 调度规划: entities=%s → dispatch_jobs≈%s (entities_per_job=%s, %s), "
        "workers=%s (%s), prefetch=%s, "
        "内存预算=%.0fMB (floor=%.0fMB), mb_per_entity=%.3f (%s), 单 job 预算≈%.1fMB",
        log_label,
        total_entities,
        plan.dispatch_jobs,
        plan.entities_per_job,
        plan.source_entities_per_job,
        plan.max_workers,
        plan.source_max_workers,
        plan.prefetch_ahead,
        plan.memory_budget_mb,
        plan.memory_floor_mb,
        plan.mb_per_entity,
        plan.source_mb_per_entity,
        plan.worker_job_budget_mb,
    )
    if ep_source == "auto" and entities_per_job >= ep_max:
        logger.warning(
            "%s: entities_per_job 已顶到上限 %s（可增大 entities_per_job_max "
            "或调大 mb_per_entity_staged / 探针 safety）",
            log_label,
            plan.entities_per_job,
        )
    if plan.max_workers < cpu_workers:
        logger.warning(
            "%s: max_workers 已由内存收紧: %s → %s（预算 %.0fMB，单 job≈%.1fMB）",
            log_label,
            cpu_workers,
            plan.max_workers,
            plan.memory_budget_mb,
            plan.worker_job_budget_mb,
        )
    return plan
