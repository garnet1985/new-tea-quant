#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
JobSource 基类/接口定义
"""

from abc import ABC, abstractmethod
from typing import Any, List


class JobSource(ABC):
    """
    任务源基类
    
    职责：负责 job 的产生与顺序
    - 与 DB 或外部系统解耦，关注"提供 jobs，而不是如何执行"
    """
    
    @abstractmethod
    def get_batch(self, size: int) -> List[Any]:
        """
        获取一批任务
        
        Args:
            size: 批次大小
        
        Returns:
            任务列表
        """
        pass
    
    @abstractmethod
    def has_more(self) -> bool:
        """
        是否还有更多任务
        
        Returns:
            True 如果还有任务，False 否则
        """
        pass
    
    @abstractmethod
    def total_count(self) -> int:
        """
        获取任务总数
        
        Returns:
            任务总数（如果未知，返回 -1）
        """
        pass
    
    def reset(self) -> None:
        """
        重置任务源（可选实现）
        """
        pass
