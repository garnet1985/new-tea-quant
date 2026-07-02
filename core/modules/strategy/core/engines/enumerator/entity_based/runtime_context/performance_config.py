"""entity_based 模式 performance 配置（简化版）。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class PerformanceConfig:
    """性能配置（传递给BacktestEngine）。"""

    reserve_cores: int = 2              # 预留核心数
    max_parallel_jobs: int = 0          # 最大并行job数（0表示自动）
    memory_budget_mb: int = 0           # 内存预算（0表示自动）
    entities_per_job: int = 1           # 每job的entity数量
    worker_memory_fraction: float = 0.85  # worker内存占比
    prefetch_ahead: int = 1             # 预取数量

    @classmethod
    def init(cls) -> PerformanceConfig:
        """初始化性能配置（hard code）。"""
        return cls(
            reserve_cores=2,
            max_parallel_jobs=0,
            memory_budget_mb=0,
            entities_per_job=1,
            worker_memory_fraction=0.85,
            prefetch_ahead=1,
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为dict（传递给BacktestEngine）。"""
        return {
            "reserve_cores": self.reserve_cores,
            "max_parallel_jobs": self.max_parallel_jobs,
            "memory_budget_mb": self.memory_budget_mb,
            "entities_per_job": self.entities_per_job,
            "worker_memory_fraction": self.worker_memory_fraction,
            "prefetch_ahead": self.prefetch_ahead,
        }


__all__ = ["PerformanceConfig"]