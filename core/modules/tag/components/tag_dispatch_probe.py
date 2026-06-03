"""Tag 调度探针：先跑 1 个 worker job，用实测 RSS 校准 dispatch_planner。"""
from __future__ import annotations

import logging
import multiprocessing as mp
import pickle
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from core.infra.job_pipeline.types import JobContext
from core.modules.tag.components.job_staging.worker_runtime import release_worker_runtime

logger = logging.getLogger(__name__)

DEFAULT_PROBE_ENTITIES: int = 20
DEFAULT_PROBE_SAFETY_FACTOR: float = 1.25


@dataclass(frozen=True)
class TagDispatchProbeResult:
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
    """仅在 auto 规划且未手写内存估算时跑探针。"""
    if performance.get("dispatch_probe") is False:
        return False
    if entities_per_job_explicit:
        return False
    if "mb_per_entity_staged" in performance:
        return False
    if total_entities < 2:
        return False
    return True


def _probe_execute(payload: Dict[str, Any]) -> Dict[str, Any]:
    """子进程内跑与生产相同的 execute 路径并采样 RSS。"""
    from core.modules.tag.tag_manager import TagManager

    rss_before_mb = _process_rss_mb()
    payload = dict(payload)
    payload["_stage_in_worker"] = True
    payload["_dispatch_probe"] = True
    ctx = JobContext(
        job_id=str(payload.get("_job_id") or "tag_probe"),
        payload=payload,
        run_name=str(payload.get("_run_name") or "tag:probe"),
    )
    t0 = time.perf_counter()
    try:
        out = TagManager._execute_single_job(ctx)
        if not isinstance(out, dict):
            out = {"success": True, "data": out}
    finally:
        release_worker_runtime()
    rss_after_mb = _process_rss_mb()
    wall_sec = time.perf_counter() - t0
    entities = payload.get("entities")
    n_entities = (
        len(entities)
        if isinstance(entities, list) and entities
        else (1 if payload.get("entity_id") else 0)
    )
    n_entities = max(1, n_entities)
    staged = out if isinstance(out, dict) else {}
    pickle_bytes = 0
    try:
        pickle_bytes = len(pickle.dumps(staged, protocol=pickle.HIGHEST_PROTOCOL))
    except Exception:
        pass
    return {
        "success": bool(staged.get("success", True)),
        "peak_rss_mb": max(rss_before_mb, rss_after_mb),
        "rss_before_mb": rss_before_mb,
        "rss_delta_mb": max(0.0, rss_after_mb - rss_before_mb),
        "entities_sampled": n_entities,
        "pickle_bytes": pickle_bytes,
        "wall_sec": wall_sec,
    }


def _process_rss_mb() -> float:
    try:
        import os

        import psutil

        return float(psutil.Process(os.getpid()).memory_info().rss) / (1024.0 * 1024.0)
    except Exception:
        return 0.0


def run_tag_dispatch_probe(
    probe_job_payload: Dict[str, Any],
    *,
    performance: Optional[Dict[str, Any]] = None,
) -> TagDispatchProbeResult:
    """
    在独立子进程跑 1 个 job（与生产相同的 stage+算路径），返回 per-entity 内存估算。
    """
    performance = performance or {}
    safety = max(1.0, float(performance.get("dispatch_probe_safety_factor", DEFAULT_PROBE_SAFETY_FACTOR)))
    start_method = str(performance.get("start_method", "spawn"))

    from core.modules.tag.components.job_staging.worker_runtime import (
        _wait_pool_children_done,
    )

    ctx = mp.get_context(start_method)
    with ctx.Pool(processes=1) as pool:
        raw = pool.apply(_probe_execute, (dict(probe_job_payload),))
    _wait_pool_children_done(timeout_sec=15.0)

    if not raw.get("success", True):
        raise RuntimeError(f"Tag dispatch probe job failed: {raw!r}")

    entities = max(1, int(raw.get("entities_sampled") or 1))
    peak_mb = max(0.1, float(raw.get("peak_rss_mb") or 0.1))
    baseline_mb = max(0.0, float(raw.get("rss_before_mb") or 0.0))
    delta_mb = max(0.1, peak_mb - baseline_mb)
    pickle_bytes = int(raw.get("pickle_bytes") or 0)

    mb_from_rss = (delta_mb / entities) * safety
    mb_from_pickle = (pickle_bytes / (1024.0 * 1024.0) / entities) * safety * 2.0
    mb_per_entity = max(mb_from_rss, mb_from_pickle, 0.05)

    result = TagDispatchProbeResult(
        entities_sampled=entities,
        peak_rss_mb=peak_mb,
        mb_per_entity=mb_per_entity,
        pickle_bytes=pickle_bytes,
        wall_sec=float(raw.get("wall_sec") or 0.0),
    )
    logger.info(
        "Tag 调度探针: entities=%s, worker_rss %.1f→%.1fMB (Δ%.1f), pickle=%.1fKB, "
        "估 %.3fMB/股 (×%.2f), wall=%.2fs",
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
