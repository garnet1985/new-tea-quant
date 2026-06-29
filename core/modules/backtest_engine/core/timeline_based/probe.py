"""
Backtest Engine - Timeline-based Probe

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
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

DEFAULT_PROBE_ENTITIES: int = 20
DEFAULT_PROBE_SAFETY_FACTOR: float = 1.25

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
        """构建探针jobs（小批次）。
        
        Args:
            jobs: 待执行的job列表
            probe_entities_count: 探针entity数量
            
        Returns:
            List[Dict[str, Any]]: 探针jobs（小批次）
        """
        if probe_entities_count <= 0:
            return []
        
        # 从jobs中取前N个entity作为探针样本
        probe_jobs = jobs[:probe_entities_count]
        
        logger.info(
            "构建探针jobs: entities=%s/%s",
            len(probe_jobs),
            len(jobs),
        )
        
        return probe_jobs
    
    @staticmethod
    def dispatch(
        probe_jobs: List[Dict[str, Any]],
        executor: str,
        performance: Dict[str, Any],
        log_label: str = "调度",
    ) -> ProbeResult:
        """执行探针（子进程测量内存和时间）。
        
        Args:
            probe_jobs: 探针jobs
            executor: 执行器标识字符串（"tag", "strategy.enum", "strategy.price"）
            performance: 配置字典
            log_label: 日志标签
            
        Returns:
            ProbeResult: 探针测量结果
        """
        if not probe_jobs:
            return Probe._get_default_result(performance)
        
        # 构建探针payload
        entities_sampled = len(probe_jobs)
        probe_payload = {
            "jobs": probe_jobs,
            "_probe_executor": executor,
            "_probe_entity_count": entities_sampled,
        }
        
        # 在子进程中运行探针
        raw_result = Probe._run_probe_in_subprocess(
            probe_payload, executor, performance, log_label
        )
        
        # 构建探针结果
        return Probe._build_probe_result(
            raw_result, entities_sampled, performance, log_label
        )
    
    @staticmethod
    def _run_probe_in_subprocess(
        probe_payload: Dict[str, Any],
        executor: str,
        performance: Dict[str, Any],
        log_label: str,
    ) -> Dict[str, Any]:
        """在独立子进程运行探针。
        
        Args:
            probe_payload: 探针payload
            executor: 执行器标识字符串
            performance: 配置字典
            log_label: 日志标签
            
        Returns:
            Dict[str, Any]: 子进程返回的原始结果
        """
        from core.infra.db.engines.duckdb.process_pool_scope import (
            is_duckdb_backend,
            is_main_duckdb_worker_pool_active,
            prepare_main_for_worker_pool,
            restore_after_worker_pool,
            wait_pool_children_done,
        )
        
        start_method = str(performance.get("start_method", "spawn"))
        
        prepared_here = False
        if is_duckdb_backend():
            wait_pool_children_done(timeout_sec=30.0)
            if not is_main_duckdb_worker_pool_active():
                prepare_main_for_worker_pool(None)
                prepared_here = True
        
        try:
            ctx = mp.get_context(start_method)
            with ctx.Pool(processes=1) as pool:
                raw = pool.apply(_probe_worker, (probe_payload,))
            wait_pool_children_done(timeout_sec=15.0)
            return raw
        finally:
            if prepared_here:
                restore_after_worker_pool()
    
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


def _probe_worker(payload: Dict[str, Any]) -> Dict[str, Any]:
    """子进程探针worker（测量执行前后RSS和时间）。
    
    Args:
        payload: 探针payload
        
    Returns:
        Dict[str, Any]: 测量结果
    """
    rss_before_mb = _process_rss_mb()
    t0 = time.perf_counter()
    
    # 执行探针payload
    out = _run_probe_executor(dict(payload))
    if not isinstance(out, dict):
        out = {"success": True, "data": out}
    
    rss_after_mb = _process_rss_mb()
    wall_sec = time.perf_counter() - t0
    entities = max(1, int(payload.get("_probe_entity_count") or 1))
    
    # 测量pickle大小
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


def _run_probe_executor(payload: Dict[str, Any]) -> Dict[str, Any]:
    """执行探针payload（根据executor标识选择执行器）。
    
    Args:
        payload: 探针payload
        
    Returns:
        Dict[str, Any]: 执行结果
    """
    key = str(payload.get("_probe_executor") or "").strip()
    
    if key == PROBE_EXECUTOR_STRATEGY_ENUM:
        from core.modules.strategy.services.execution.enum_dispatch_probe import (
            execute_enum_probe_payload,
        )
        return execute_enum_probe_payload(payload)
    
    if key == PROBE_EXECUTOR_STRATEGY_PRICE:
        from core.modules.strategy.services.execution.price_dispatch_probe import (
            execute_price_probe_payload,
        )
        return execute_price_probe_payload(payload)
    
    if key == PROBE_EXECUTOR_TAG:
        from core.modules.tag.engines.shared.dispatch_probe import (
            execute_tag_probe_payload,
        )
        return execute_tag_probe_payload(payload)
    
    raise ValueError(f"未知探针执行器: {key!r}")


__all__ = [
    "ProbeResult",
    "WorkerProbe",
    "Probe",
    "DEFAULT_PROBE_ENTITIES",
    "DEFAULT_PROBE_SAFETY_FACTOR",
    "PROBE_EXECUTOR_TAG",
    "PROBE_EXECUTOR_STRATEGY_ENUM",
    "PROBE_EXECUTOR_STRATEGY_PRICE",
]