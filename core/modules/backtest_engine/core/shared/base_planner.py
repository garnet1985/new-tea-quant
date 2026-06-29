"""
Backtest Engine - Base Planner

抽象基类，定义共享的抽象方法。

职责：
- 定义对外API（plan_jobs）
- 定义共享的机器容量获取（_get_machine_capacity）
- 不强制固定流程（子类自由实现）

特点：
- 只定义真正共享的部分
- 不强制5步骤命名
- 子类自由实现内部逻辑（Timeline/Slice不同）
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MachineCapacity:
    """机器容量（共享数据类型）。"""
    
    cpu_count: int
    memory_budget_mb: float
    memory_floor_mb: float
    reserve_cores: int


class BasePlanner(ABC):
    """调度规划器抽象基类。
    
    只定义真正共享的部分：
    - plan_jobs()：对外API（编排层）
    - _get_machine_capacity()：获取机器容量（共享machine_info）
    
    子类自由实现：
    - 内部规划逻辑（Timeline: entity-based, Slice: 读算分离）
    - 探针逻辑（Timeline: entity探针, Slice: slice探针）
    - 切割逻辑（Timeline: entity切割, Slice: slice切割）
    """
    
    @classmethod
    @abstractmethod
    def plan_jobs(
        cls,
        jobs: List[Dict[str, Any]],
        performance: Dict[str, Any],
        executor: Optional[Any] = None,
        log_label: str = "调度",
    ) -> Tuple[Any, List[Any]]:
        """Planner的编排层（对外API）。
        
        Args:
            jobs: 待调度的jobs列表
            performance: 配置字典
            executor: 执行器（可选）
            log_label: 日志标签
            
        Returns:
            Tuple[Any, List[Any]]: 规划结果和job批次（具体类型由子类定义）
        """
        pass
    
    @classmethod
    def _get_machine_capacity(
        cls,
        performance: Dict[str, Any],
    ) -> MachineCapacity:
        """获取机器容量（共享实现）。
        
        Args:
            performance: 配置字典
            
        Returns:
            MachineCapacity: 机器容量
        """
        from core.modules.backtest_engine.core.shared.machine_info import MachineInfo
        return MachineInfo.get_capacity(performance)


__all__ = [
    "MachineCapacity",
    "BasePlanner",
]