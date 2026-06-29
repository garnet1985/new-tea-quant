"""
Backtest Engine - Machine Info (Shared)

共享机器配置信息获取API（timeline和slice模式共用）。
"""
from __future__ import annotations

import multiprocessing as mp
from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class MachineCapacity:
    """机器容量信息。"""
    
    cpu_count: int
    memory_budget_mb: float
    memory_floor_mb: float
    reserve_cores: int


class MachineInfo:
    """机器信息获取（面向对象方式）。"""
    
    @staticmethod
    def get_capacity(performance: Dict[str, Any]) -> MachineCapacity:
        """获取机器容量信息（CPU和内存预算）。
        
        Args:
            performance: 配置字典
            
        Returns:
            MachineCapacity: 机器容量结果
        """
        cpu_count = MachineInfo.get_cpu_count()
        reserve_cores = MachineInfo.get_reserve_cores(performance)
        
        memory_budget_mb = MachineInfo.get_memory_budget(performance)
        memory_floor_mb = MachineInfo.get_memory_floor(performance)
        
        return MachineCapacity(
            cpu_count=cpu_count,
            memory_budget_mb=memory_budget_mb,
            memory_floor_mb=memory_floor_mb,
            reserve_cores=reserve_cores,
        )
    
    @staticmethod
    def get_cpu_count() -> int:
        """获取CPU核心数。"""
        return mp.cpu_count() or 1
    
    @staticmethod
    def get_reserve_cores(performance: Dict[str, Any]) -> int:
        """获取保留核心数。"""
        reserve_cores = performance.get("reserve_cores", 1)
        return max(1, int(reserve_cores))
    
    @staticmethod
    def get_memory_budget(performance: Dict[str, Any]) -> float:
        """获取内存预算（MB）。"""
        memory_budget_mb = performance.get("memory_budget_mb", 4096.0)
        return max(1024.0, float(memory_budget_mb))
    
    @staticmethod
    def get_memory_floor(performance: Dict[str, Any]) -> float:
        """获取内存底线（MB）。"""
        memory_floor_mb = performance.get("memory_floor_mb", 1024.0)
        return max(512.0, float(memory_floor_mb))
    
    @staticmethod
    def get_available_workers(capacity: MachineCapacity) -> int:
        """获取可用的worker数量（CPU数 - 预留核心）。"""
        return max(1, capacity.cpu_count - capacity.reserve_cores)


__all__ = [
    "MachineCapacity",
    "MachineInfo",
]