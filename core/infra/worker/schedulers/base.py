#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Scheduler 基类/接口定义
"""

from abc import ABC, abstractmethod
from typing import Any, List


class Scheduler(ABC):
    """
    调度器基类
    
    职责：基于监控数据和配置策略，动态调整参数
    - 以 orchestrator 角色存在：
      - 从 Queue 拉取一批 jobs
      - 调用 Executor 执行
      - 把结果交给 Aggregator & ErrorHandler
      - 同时更新 Monitor
    """
    
    @abstractmethod
    def get_next_batch_size(self) -> int:
        """
        获取下一批的批次大小
        
        Returns:
            批次大小
        """
        pass
    
    @abstractmethod
    def update_after_batch(
        self,
        batch_size: int,
        batch_results: List[Any],
        finished_jobs: int,
    ) -> None:
        """
        在批次执行完成后更新调度器状态
        
        Args:
            batch_size: 批次大小
            batch_results: 批次执行结果
            finished_jobs: 已完成的任务总数
        """
        pass
    
    def reset(self) -> None:
        """
        重置调度器状态（可选实现）
        """
        pass
