#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Monitor 基类/接口定义
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class Monitor(ABC):
    """
    监控器基类
    
    职责：观测指标，提供可观测性
    - 不直接做决策，只提供「可观测性」
    """
    
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """
        获取监控统计信息
        
        Returns:
            统计信息字典
        """
        pass
    
    @abstractmethod
    def get_warnings(self) -> List[str]:
        """
        获取告警信息
        
        Returns:
            告警信息列表（如果没有告警，返回空列表）
        """
        pass
    
    def update(self, **kwargs) -> None:
        """
        更新监控状态（可选实现）
        
        Args:
            **kwargs: 更新参数
        """
        pass
    
    def export_snapshot(self) -> Optional[Dict[str, Any]]:
        """
        导出监控快照（可选实现）
        
        Returns:
            快照字典，或 None
        """
        return None
