"""
Backtest Engine - Execution Context

entity_based / slice_based 共享执行上下文（pickle 传递到子进程）。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class ExecutionContext:
    """Backtest 执行上下文（pickle 传递到子进程）。"""
    
    # 运行时信息（主进程初始化）
    task_name: str
    total_jobs: int
    start_time: float
    
    # 进度信息（子进程更新）
    finished_jobs: int = 0
    success_count: int = 0
    fail_count: int = 0
    
    # 配置信息
    executor: str = ""
    performance: Dict[str, Any] = field(default_factory=dict)
    
    # 业务数据（可选）
    business_data: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def create(
        cls,
        task_name: str,
        total_jobs: int,
        executor: str = "",
        performance: Optional[Dict[str, Any]] = None,
        business_data: Optional[Dict[str, Any]] = None,
    ) -> ExecutionContext:
        """创建ExecutionContext（工厂方法）。
        
        Args:
            task_name: 运行名称
            total_jobs: 总job数量
            executor: 执行器标识
            performance: 配置字典
            business_data: 业务数据
            
        Returns:
            ExecutionContext: 执行上下文
        """
        return cls(
            task_name=task_name,
            total_jobs=total_jobs,
            start_time=time.monotonic(),
            finished_jobs=0,
            success_count=0,
            fail_count=0,
            executor=executor,
            performance=performance or {},
            business_data=business_data or {},
        )
    
    def update_progress(self, success: bool) -> None:
        """更新进度（子进程调用）。
        
        Args:
            success: 是否成功
        """
        self.finished_jobs += 1
        if success:
            self.success_count += 1
        else:
            self.fail_count += 1
    
    def elapsed_seconds(self) -> float:
        """计算已耗时（秒）。
        
        Returns:
            float: 已耗时秒数
        """
        return time.monotonic() - self.start_time
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于日志或持久化）。
        
        Returns:
            Dict[str, Any]: 字典表示
        """
        return {
            "task_name": self.task_name,
            "total_jobs": self.total_jobs,
            "finished_jobs": self.finished_jobs,
            "success_count": self.success_count,
            "fail_count": self.fail_count,
            "elapsed_seconds": self.elapsed_seconds(),
            "executor": self.executor,
            "performance": self.performance,
            "business_data": self.business_data,
        }


__all__ = ["ExecutionContext"]