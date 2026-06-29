"""
Backtest Engine - Slice-based Probe

切片模式的探针逻辑（读算分离特殊处理）。

职责：
- SliceProbe.should_run()：判断是否需要探针
- SliceProbe.build_probe_jobs()：构建探针jobs（slice特殊）
- SliceProbe.dispatch()：执行探针（测量slice内存和时间）

特点：
- slice探针测量读算分离的内存消耗
- Reader进程内存 + Compute进程内存
- 管道队列数据传递内存
"""
from __future__ import annotations

import logging
import time
import pickle
import multiprocessing as mp
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from core.modules.backtest_engine.core.shared.machine_info import MachineCapacity

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SliceProbeResult:
    """切片探针结果。"""
    
    # Slice内存消耗
    mb_per_slice_reader: float  # Reader进程的每slice内存
    mb_per_slice_compute: float  # Compute进程的每slice内存
    mb_per_slice_payload: float  # Payload传递的每slice内存
    
    # Slice时间消耗
    sec_per_slice_reader: float  # Reader读取每slice时间
    sec_per_slice_compute: float  # Compute计算每slice时间
    
    # 探针统计
    slices_sampled: int
    wall_sec: float
    peak_rss_mb_reader: float
    peak_rss_mb_compute: float


class SliceProbe:
    """切片探针（读算分离特殊处理）。
    
    职责：
    - 判断是否需要探针
    - 构建探针jobs
    - 执行探针测量
    """
    
    @staticmethod
    def should_run(
        jobs: List[Dict[str, Any]],
        performance: Dict[str, Any],
    ) -> bool:
        """判断是否需要运行探针。
        
        Args:
            jobs: 待执行的job列表
            performance: 配置字典
            
        Returns:
            bool: 是否需要探针
        """
        # 用户指定了reader_workers和queue_capacity，跳过探针
        if performance.get("slice_probe") is False:
            return False
        
        # 用户指定了reader_workers和queue_capacity，跳过探针
        if (
            performance.get("reader_workers") not in (None, "", "auto")
            and performance.get("queue_capacity") not in (None, "", "auto")
        ):
            return False
        
        # 用户指定了内存消耗，跳过探针
        if performance.get("mb_per_slice_staged") not in (None, ""):
            return False
        
        # jobs数量太少，跳过探针
        if len(jobs) < 1:
            return False
        
        return True
    
    @staticmethod
    def build_probe_jobs(
        jobs: List[Dict[str, Any]],
        capacity: MachineCapacity,
        performance: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """构建探针jobs（slice特殊）。
        
        Args:
            jobs: 待执行的job列表
            capacity: 机器容量
            performance: 配置字典
            
        Returns:
            List[Dict]: 探针jobs（小批次slice测量）
        """
        # 探针slice数量（默认2个slice）
        probe_slice_count = int(performance.get("probe_slice_count", 2))
        
        # 从jobs中选取前N个slice作为探针样本
        probe_jobs = []
        for i, job in enumerate(jobs[:probe_slice_count]):
            probe_job = dict(job)
            probe_job["_probe_slice_index"] = i
            probe_job["_is_probe"] = True
            probe_jobs.append(probe_job)
        
        logger.info(
            "Slice探针jobs: slices=%s, probe_count=%s",
            len(jobs),
            len(probe_jobs),
        )
        
        return probe_jobs
    
    @staticmethod
    def dispatch(
        probe_jobs: List[Dict[str, Any]],
        *,
        executor: str,
        performance: Dict[str, Any],
        log_label: str = "Slice探针",
    ) -> SliceProbeResult:
        """执行slice探针（读算分离测量）。
        
        测量读算分离的内存消耗：
        - Reader进程内存（mb_per_slice_reader）
        - Compute进程内存（mb_per_slice_compute）
        - Payload传递内存（mb_per_slice_payload）
        
        Args:
            probe_jobs: 探针jobs
            executor: 执行器标识（字符串）
            performance: 配置字典
            log_label: 日志标签
            
        Returns:
            SliceProbeResult: 探针结果
        """
        if not probe_jobs:
            # 返回默认值
            return SliceProbeResult(
                mb_per_slice_reader=10.0,
                mb_per_slice_compute=15.0,
                mb_per_slice_payload=5.0,
                sec_per_slice_reader=0.1,
                sec_per_slice_compute=0.2,
                slices_sampled=0,
                wall_sec=0.0,
                peak_rss_mb_reader=10.0,
                peak_rss_mb_compute=15.0,
            )
        
        logger.info(
            "%s启动: executor=%s, slices=%s",
            log_label,
            executor,
            len(probe_jobs),
        )
        
        # TODO: 实现实际slice探针执行（调用真实的读算分离执行）
        # 当前为简化版：使用启发式规则
        
        # 启发式规则（基于经验数据）
        mb_per_slice_reader = 20.0  # Reader进程每slice内存（MB）
        mb_per_slice_compute = 30.0  # Compute进程每slice内存（MB）
        mb_per_slice_payload = 2.0   # Payload每slice内存（MB）
        
        sec_per_slice_reader = 0.15  # Reader读取每slice时间（秒）
        sec_per_slice_compute = 0.25  # Compute计算每slice时间（秒）
        
        slices_sampled = len(probe_jobs)
        wall_sec = (sec_per_slice_reader + sec_per_slice_compute) * slices_sampled
        
        # Peak RSS估算（Reader和Compute进程）
        peak_rss_mb_reader = mb_per_slice_reader * 2  # Reader peak（2个slice并发）
        peak_rss_mb_compute = mb_per_slice_compute * 1  # Compute peak（单进程）
        
        logger.info(
            "%s完成: reader=%.1fMB/slice, compute=%.1fMB/slice, "
            "payload=%.1fMB/slice, wall=%.2fs, slices=%s",
            log_label,
            mb_per_slice_reader,
            mb_per_slice_compute,
            mb_per_slice_payload,
            wall_sec,
            slices_sampled,
        )
        
        return SliceProbeResult(
            mb_per_slice_reader=mb_per_slice_reader,
            mb_per_slice_compute=mb_per_slice_compute,
            mb_per_slice_payload=mb_per_slice_payload,
            sec_per_slice_reader=sec_per_slice_reader,
            sec_per_slice_compute=sec_per_slice_compute,
            slices_sampled=slices_sampled,
            wall_sec=wall_sec,
            peak_rss_mb_reader=peak_rss_mb_reader,
            peak_rss_mb_compute=peak_rss_mb_compute,
        )


__all__ = [
    "SliceProbeResult",
    "SliceProbe",
]