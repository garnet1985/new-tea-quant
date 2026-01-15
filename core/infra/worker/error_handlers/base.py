#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ErrorHandler 基类/接口定义
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict

from ..executors.base import JobResult


class ErrorAction(Enum):
    """错误处理动作"""
    RETRY = "retry"      # 重试
    SKIP = "skip"       # 跳过
    ABORT = "abort"     # 中止


class ErrorHandler(ABC):
    """
    错误处理器基类
    
    职责：统一处理 job 级别的异常
    - 是否重试（次数 / 退避策略）
    - 是否跳过某些已知安全异常
    - 何时 fail-fast
    """
    
    @abstractmethod
    def handle_error(
        self,
        job: Dict[str, Any],
        error: Exception,
        retry_count: int = 0,
    ) -> ErrorAction:
        """
        处理错误
        
        Args:
            job: 失败的任务
            error: 异常对象
            retry_count: 当前重试次数
        
        Returns:
            错误处理动作
        """
        pass
    
    def should_retry(
        self,
        job: Dict[str, Any],
        error: Exception,
        retry_count: int,
    ) -> bool:
        """
        判断是否应该重试（可选实现）
        
        Args:
            job: 失败的任务
            error: 异常对象
            retry_count: 当前重试次数
        
        Returns:
            True 如果应该重试，False 否则
        """
        return False
    
    def get_retry_delay(self, retry_count: int) -> float:
        """
        获取重试延迟时间（秒）（可选实现）
        
        Args:
            retry_count: 当前重试次数
        
        Returns:
            延迟时间（秒）
        """
        return 0.0
