"""
Backtest Engine - entity_based Probe

时间线模式的探针逻辑：构建探针jobs + 执行探针测量。

职责：
- Probe.should_run()：判断是否需要运行探针
- Probe.build_probe_jobs()：构建探针jobs（小批次）
- Probe.dispatch()：执行探针（子进程测量内存和时间）

WorkerProbe：
- 解析max_workers='auto'（基于CPU和配置）

探针执行器标识：
- "tag"：Tag探针执行器
- "strategy.enum"：Strategy Enum探针执行器
- "strategy.price"：Strategy Price探针执行器
"""
from __future__ import annotations

import logging
import multiprocessing as mp
import pickle
import time
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Union

from core.modules.backtest_engine.core.shared.job_lifecycle import run_job_lifecycle
from core.modules.backtest_engine.core.shared.types import JobContext, TaskStartFn, TaskCompleteFn

logger = logging.getLogger(__name__)

DEFAULT_PROBE_ENTITIES: int = 20
DEFAULT_PROBE_SAFETY_FACTOR: float = 1.25
# 探针只测内存/耗时，不跑全量回测区间（calendar 日数过大会极慢）
PROBE_LOOKBACK_CALENDAR_DAYS: int = 60

# spawn 下须用模块级 worker + 字符串选择执行器（不可 pickle 闭包）
PROBE_EXECUTOR_TAG = "tag"
PROBE_EXECUTOR_STRATEGY_ENUM = "strategy.enum"
PROBE_EXECUTOR_STRATEGY_PRICE = "strategy.price"


@dataclass(frozen=True)
class ProbeResult:
    """探针测量结果。"""
    
    entities_sampled: int
    peak_rss_mb: float
    mb_per_entity: float
    sec_per_entity: float
    pickle_bytes: int
    wall_sec: float


class WorkerProbe:
    """Worker并行度探针（解析max_workers）。"""
    
    @classmethod
    def resolve(
        cls,
        max_workers: Union[str, int],
        *,
        reserve_cores: int = 1,
        cap: Optional[int] = None,
    ) -> int:
        """解析max_workers='auto'。"""
        if isinstance(max_workers, str) and max_workers.lower() == "auto":
            resolved = cls._auto(reserve_cores=reserve_cores, cap=cap)
            logger.info(
                "Worker数量（auto/probe）: %s (cpu=%s, reserve=%s, cap=%s)",
                resolved,
                mp.cpu_count(),
                reserve_cores,
                cap,
            )
            return resolved
        
        validated = cls._validate_int(int(max_workers))
        if validated != max_workers:
            logger.warning(
                "Worker数量超过上限，已调整: %s → %s (max=%s)",
                max_workers,
                validated,
                (mp.cpu_count() or 1) * 2,
            )
        return validated
    
    @staticmethod
    def _auto(*, reserve_cores: int, cap: Optional[int]) -> int:
        cpu_count = mp.cpu_count() or 1
        reserve = max(0, min(int(reserve_cores), cpu_count - 1))
        workers = max(1, cpu_count - reserve)
        if cap is not None:
            workers = min(workers, max(1, int(cap)))
        return WorkerProbe._validate_int(workers)
    
    @staticmethod
    def _validate_int(max_workers: int) -> int:
        cpu_count = mp.cpu_count() or 1
        max_allowed = cpu_count * 2
        return min(max(1, max_workers), max_allowed)


class Probe:
    """时间线模式探针（面向对象方式）。"""
    
    @staticmethod
    def should_run(
        performance: Dict[str, Any],
        total_entities: int,
    ) -> bool:
        """判断是否需要运行探针。
        
        Args:
            performance: 配置字典
            total_entities: 总entity数量
            
        Returns:
            bool: 是否需要运行探针
        """
        if performance.get("dispatch_probe") is False:
            return False
        if performance.get("entities_per_job") not in (None, "", "auto"):
            return False
        if performance.get("mb_per_entity_staged") not in (None, ""):
            return False
        if total_entities < 1:
            return False
        return True
    
    @staticmethod
    def build_probe_jobs(
        jobs: List[Dict[str, Any]],
        probe_entities_count: int,
    ) -> List[Dict[str, Any]]:
        """构建探针jobs（Bundle模式）。

        Args:
            jobs: bundle job列表（单个bundle job）
            probe_entities_count: 探针entity数量

        Returns:
            List[Dict[str, Any]]: 探针bundle job（切割entity_specified）
        """
        if probe_entities_count <= 0:
            return []

        # Bundle模式：切割entity_specified，构建新的bundle job
        bundle_job = jobs[0]
        payload = bundle_job["payload"]

        entity_specified = payload.get("entity_specified", [])
        probe_entity_specified = entity_specified[:probe_entities_count]

        entity_shared = Probe._shorten_entity_shared_for_probe(
            payload.get("entity_shared", {})
        )

        # 构建探针 bundle job（缩短日期窗口；其余业务字段透传）
        probe_bundle_payload = {
            k: v
            for k, v in payload.items()
            if k not in {"entity_specified", "entity_shared", "entities_count", "_dispatch_probe"}
        }
        probe_bundle_payload["entity_specified"] = probe_entity_specified
        probe_bundle_payload["entity_shared"] = entity_shared
        probe_bundle_payload["entities_count"] = len(probe_entity_specified)
        probe_bundle_payload["_dispatch_probe"] = True

        probe_jobs = [{
            "id": bundle_job["id"],
            "payload": probe_bundle_payload,
        }]

        logger.info(
            "构建探针jobs: entities=%s/%s",
            len(probe_entity_specified),
            len(entity_specified),
        )

        return probe_jobs

    @staticmethod
    def _shorten_entity_shared_for_probe(entity_shared: Dict[str, Any]) -> Dict[str, Any]:
        """探针用短窗口加载 K 线（仅估 mb/entity，不跑全区间）。"""
        shortened = deepcopy(entity_shared or {})
        for data_key, decl in shortened.items():
            if not isinstance(decl, dict):
                continue
            end = str(decl.get("end") or "").strip()
            if len(end) != 8 or not end.isdigit():
                continue
            try:
                end_dt = datetime.strptime(end, "%Y%m%d")
            except ValueError:
                continue
            start_dt = end_dt - timedelta(days=PROBE_LOOKBACK_CALENDAR_DAYS)
            decl["start"] = start_dt.strftime("%Y%m%d")
            logger.info(
                "探针缩短数据窗口：%s %s → %s",
                data_key,
                decl["start"],
                end,
            )
        return shortened
    
    @staticmethod
    def dispatch(
        probe_jobs: List[Dict[str, Any]],
        performance: Dict[str, Any],
        execute_fn: Optional[Callable[[JobContext], Dict[str, Any]]],
        log_label: str = "调度",
        task_name: str = "",
        *,
        on_before_task_start: Optional[TaskStartFn] = None,
        on_after_task_complete: Optional[TaskCompleteFn] = None,
    ) -> ProbeResult:
        """执行探针（子进程测量内存和时间）。"""
        if not probe_jobs:
            return Probe._get_default_result(performance)

        if execute_fn is None:
            logger.warning("%s探针跳过：未提供 execute_fn", log_label)
            return Probe._get_default_result(performance)

        entities_sampled = len(
            probe_jobs[0].get("payload", {}).get("entity_specified") or []
        )
        print(
            f"  探针测量中 ({entities_sampled} entities，用于调度 batch，请稍候)…",
            flush=True,
        )
        probe_job = probe_jobs[0]
        probe_payload = dict(probe_job.get("payload") or {})
        probe_payload["_probe_entity_count"] = entities_sampled
        probe_payload["_job_id"] = str(probe_job.get("id") or "probe")

        raw_result = Probe._run_probe_in_subprocess(
            execute_fn,
            probe_payload,
            task_name or f"{log_label}:probe",
            performance,
            log_label,
            on_before_task_start=on_before_task_start,
            on_after_task_complete=on_after_task_complete,
        )

        return Probe._build_probe_result(
            raw_result, entities_sampled, performance, log_label
        )

    @staticmethod
    def _run_probe_in_subprocess(
        execute_fn: Callable[[JobContext], Dict[str, Any]],
        probe_payload: Dict[str, Any],
        task_name: str,
        performance: Dict[str, Any],
        log_label: str,
        *,
        on_before_task_start: Optional[TaskStartFn] = None,
        on_after_task_complete: Optional[TaskCompleteFn] = None,
    ) -> Dict[str, Any]:
        """在独立子进程运行探针（默认主进程内试跑，避免嵌套进程池 + DuckDB 锁）。"""
        worker_args = (
            execute_fn,
            probe_payload,
            task_name,
            on_before_task_start,
            on_after_task_complete,
        )
        if not bool(performance.get("probe_in_subprocess", False)):
            logger.info("%s探针：主进程内试跑（缩短窗口）", log_label)
            print("  探针：主进程内试跑…", flush=True)
            return _probe_worker(worker_args)

        from core.infra.db import Db

        start_method = str(performance.get("start_method", "spawn"))
        wp = Db.duckdb.worker_pool

        prepared_here = False
        if wp.is_backend():
            wp.wait_pool_children_done(timeout_sec=30.0)
            if not wp.is_main_active():
                wp.prepare_main(None)
                prepared_here = True

        try:
            ctx = mp.get_context(start_method)
            with ctx.Pool(processes=1) as pool:
                raw = pool.apply(_probe_worker, (worker_args,))
            wp.wait_pool_children_done(timeout_sec=15.0)
            return raw
        finally:
            if prepared_here:
                wp.restore_after()
    
    @staticmethod
    def _build_probe_result(
        raw: Dict[str, Any],
        entities_sampled: int,
        performance: Dict[str, Any],
        log_label: str,
    ) -> ProbeResult:
        """构建探针结果（计算mb_per_entity）。
        
        Args:
            raw: 子进程返回的原始结果
            entities_sampled: 探针entity数量
            performance: 配置字典
            log_label: 日志标签
            
        Returns:
            ProbeResult: 探针测量结果
        """
        safety = max(
            1.0,
            float(performance.get("dispatch_probe_safety_factor", DEFAULT_PROBE_SAFETY_FACTOR)),
        )
        
        if not raw.get("success", True):
            raise RuntimeError(f"{log_label}探针job失败: {raw!r}")
        
        peak_mb = max(0.1, float(raw.get("peak_rss_mb") or 0.1))
        baseline_mb = max(0.0, float(raw.get("rss_before_mb") or 0.0))
        delta_mb = max(0.1, peak_mb - baseline_mb)
        pickle_bytes = int(raw.get("pickle_bytes") or 0)
        wall_sec = float(raw.get("wall_sec") or 0.0)
        
        # 计算mb_per_entity（基于RSS和pickle大小）
        mb_from_rss = (delta_mb / entities_sampled) * safety
        mb_from_pickle = (pickle_bytes / (1024.0 * 1024.0) / entities_sampled) * safety * 2.0
        mb_per_entity = max(mb_from_rss, mb_from_pickle, 0.05)
        
        result = ProbeResult(
            entities_sampled=entities_sampled,
            peak_rss_mb=peak_mb,
            mb_per_entity=mb_per_entity,
            sec_per_entity=wall_sec / entities_sampled if entities_sampled > 0 else 0.0,
            pickle_bytes=pickle_bytes,
            wall_sec=wall_sec,
        )
        
        logger.info(
            "%s探针: entities=%s, worker_rss %.1f→%.1fMB (Δ%.1f), pickle=%.1fKB, "
            "估 %.3fMB/entity (×%.2f), wall=%.2fs",
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
    
    @staticmethod
    def _get_default_result(performance: Dict[str, Any]) -> ProbeResult:
        """获取默认探针结果（不运行探针时使用）。"""
        mb_per_entity = Probe._estimate_mb_per_entity(performance)
        return ProbeResult(
            entities_sampled=0,
            peak_rss_mb=0.0,
            mb_per_entity=mb_per_entity,
            sec_per_entity=0.0,
            pickle_bytes=0,
            wall_sec=0.0,
        )
    
    @staticmethod
    def _estimate_mb_per_entity(performance: Dict[str, Any]) -> float:
        """估算mb_per_entity（基于配置或默认值）。"""
        staged = performance.get("mb_per_entity_staged")
        if staged not in (None, ""):
            return max(0.01, float(staged))
        return 1.0  # 默认值


def _probe_worker(args: tuple) -> Dict[str, Any]:
    """探针 worker：init → execute_fn → release。"""
    execute_fn, payload, task_name, on_before_task_start, on_after_task_complete = args
    entities = int(payload.get("_probe_entity_count") or payload.get("entities_count") or 1)
    logger.info("探针 worker 开始：entities=%d dispatch_probe=%s", entities, payload.get("_dispatch_probe"))
    rss_before_mb = _process_rss_mb()
    t0 = time.perf_counter()

    ctx = JobContext(
        job_id=str(payload.get("_job_id") or "probe"),
        payload=dict(payload),
        task_name=task_name,
    )
    out = run_job_lifecycle(
        execute_fn,
        ctx,
        on_before_task_start=on_before_task_start,
        on_after_task_complete=on_after_task_complete,
    )
    if not isinstance(out, dict):
        out = {"success": True, "data": out}

    rss_after_mb = _process_rss_mb()
    wall_sec = time.perf_counter() - t0
    entities = max(1, int(payload.get("_probe_entity_count") or payload.get("entities_count") or 1))

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


def _process_rss_mb() -> float:
    """测量当前进程RSS（MB）。"""
    try:
        import os
        import psutil
        
        return float(psutil.Process(os.getpid()).memory_info().rss) / (1024.0 * 1024.0)
    except Exception:
        return 0.0


__all__ = [
    "ProbeResult",
    "WorkerProbe",
    "Probe",
    "DEFAULT_PROBE_ENTITIES",
    "DEFAULT_PROBE_SAFETY_FACTOR",
]