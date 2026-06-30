"""调度探针：子进程试跑真实 job 路径，用 RSS 估算 mb/entity。"""
from __future__ import annotations

import logging
import pickle
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

DEFAULT_PROBE_ENTITIES: int = 20
DEFAULT_PROBE_SAFETY_FACTOR: float = 1.25

# spawn 下须用模块级 worker + 字符串选择执行器（不可 pickle 闭包）
PROBE_EXECUTOR_TAG = "tag"
PROBE_EXECUTOR_STRATEGY_ENUM = "strategy.enum"
PROBE_EXECUTOR_STRATEGY_PRICE = "strategy.price"


@dataclass(frozen=True)
class DispatchProbeResult:
    entities_sampled: int
    peak_rss_mb: float
    mb_per_entity: float
    pickle_bytes: int
    wall_sec: float


def should_run_dispatch_probe(
    performance: Dict[str, Any],
    *,
    total_entities: int,
    entities_per_job_explicit: bool,
) -> bool:
    """auto 规划且未手写 mb_per_entity_staged 时跑探针。"""
    if performance.get("dispatch_probe") is False:
        return False
    if entities_per_job_explicit:
        return False
    if performance.get("mb_per_entity_staged") not in (None, ""):
        return False
    if total_entities < 1:
        return False
    return True


def process_rss_mb() -> float:
    try:
        import os

        import psutil

        return float(psutil.Process(os.getpid()).memory_info().rss) / (1024.0 * 1024.0)
    except Exception:
        return 0.0


def _run_probe_executor(payload: Dict[str, Any]) -> Dict[str, Any]:
    raise RuntimeError(
        "legacy infra.worker dispatch_probe executor routing was removed; "
        "use BacktestEngine.timeline.run with execute_fn"
    )


def dispatch_probe_subprocess_worker(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Pool worker（模块级，spawn 可 pickle）。"""
    rss_before_mb = process_rss_mb()
    t0 = time.perf_counter()
    out = _run_probe_executor(dict(payload))
    if not isinstance(out, dict):
        out = {"success": True, "data": out}
    rss_after_mb = process_rss_mb()
    wall_sec = time.perf_counter() - t0
    entities = max(1, int(payload.get("_probe_entity_count") or 1))
    pickle_bytes = 0
    try:
        pickle_bytes = len(pickle.dumps(out, protocol=pickle.HIGHEST_PROTOCOL))
    except Exception:
        pass
    return {
        "success": bool(out.get("success", True)),
        "peak_rss_mb": max(rss_before_mb, rss_after_mb),
        "rss_before_mb": rss_before_mb,
        "entities_sampled": entities,
        "pickle_bytes": pickle_bytes,
        "wall_sec": wall_sec,
    }


def build_probe_result(
    raw: Dict[str, Any],
    *,
    performance: Optional[Dict[str, Any]] = None,
    log_label: str = "调度",
) -> DispatchProbeResult:
    performance = performance or {}
    safety = max(
        1.0,
        float(performance.get("dispatch_probe_safety_factor", DEFAULT_PROBE_SAFETY_FACTOR)),
    )
    if not raw.get("success", True):
        raise RuntimeError(f"{log_label}探针 job 失败: {raw!r}")

    entities = max(1, int(raw.get("entities_sampled") or 1))
    peak_mb = max(0.1, float(raw.get("peak_rss_mb") or 0.1))
    baseline_mb = max(0.0, float(raw.get("rss_before_mb") or 0.0))
    delta_mb = max(0.1, peak_mb - baseline_mb)
    pickle_bytes = int(raw.get("pickle_bytes") or 0)

    mb_from_rss = (delta_mb / entities) * safety
    mb_from_pickle = (pickle_bytes / (1024.0 * 1024.0) / entities) * safety * 2.0
    mb_per_entity = max(mb_from_rss, mb_from_pickle, 0.05)

    result = DispatchProbeResult(
        entities_sampled=entities,
        peak_rss_mb=peak_mb,
        mb_per_entity=mb_per_entity,
        pickle_bytes=pickle_bytes,
        wall_sec=float(raw.get("wall_sec") or 0.0),
    )
    logger.info(
        "%s探针: entities=%s, worker_rss %.1f→%.1fMB (Δ%.1f), pickle=%.1fKB, "
        "估 %.3fMB/股 (×%.2f), wall=%.2fs",
        log_label,
        result.entities_sampled,
        baseline_mb,
        peak_mb,
        delta_mb,
        result.pickle_bytes / 1024.0,
        result.mb_per_entity,
        safety,
        result.wall_sec,
    )
    return result


def run_dispatch_probe_in_subprocess(
    probe_payload: Dict[str, Any],
    *,
    executor: str,
    performance: Optional[Dict[str, Any]] = None,
    log_label: str = "调度",
) -> DispatchProbeResult:
    """在独立子进程跑 1 次探针（与生产相同的 execute 路径）。"""
    import multiprocessing as mp

    from core.infra.db.engines.duckdb.process_pool_scope import (
        is_duckdb_backend,
        is_main_duckdb_worker_pool_active,
        prepare_main_for_worker_pool,
        restore_after_worker_pool,
        wait_pool_children_done,
    )

    performance = performance or {}
    start_method = str(performance.get("start_method", "spawn"))
    payload = dict(probe_payload)
    payload["_probe_executor"] = executor

    prepared_here = False
    if is_duckdb_backend():
        wait_pool_children_done(timeout_sec=30.0)
        if not is_main_duckdb_worker_pool_active():
            prepare_main_for_worker_pool(None)
            prepared_here = True

    try:
        ctx = mp.get_context(start_method)
        with ctx.Pool(processes=1) as pool:
            raw = pool.apply(dispatch_probe_subprocess_worker, (payload,))
        wait_pool_children_done(timeout_sec=15.0)
        return build_probe_result(raw, performance=performance, log_label=log_label)
    finally:
        if prepared_here:
            restore_after_worker_pool()
