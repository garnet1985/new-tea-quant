#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
简单错误处理器
"""

from typing import Any, Dict

from .base import ErrorAction, ErrorHandler


class SimpleErrorHandler(ErrorHandler):
    """
    简单错误处理器
    
    策略：
    - 所有错误都跳过（不重试）
    - 记录错误信息
    """
    
    def __init__(self, max_retries: int = 0):
        """
        初始化
        
        Args:
            max_retries: 最大重试次数（默认 0，不重试）
        """
        self.max_retries = max_retries
    
    def handle_error(
        self,
        job: Dict[str, Any],
        error: Exception,
        retry_count: int = 0,
    ) -> ErrorAction:
        """处理错误"""
        if retry_count < self.max_retries:
            return ErrorAction.RETRY
        return ErrorAction.SKIP
    
    def should_retry(
        self,
        job: Dict[str, Any],
        error: Exception,
        retry_count: int,
    ) -> bool:
        """判断是否应该重试"""
        return retry_count < self.max_retries
    
    def get_retry_delay(self, retry_count: int) -> float:
        """获取重试延迟时间（秒）"""
        # 简单的指数退避：1s, 2s, 4s, ...
        return min(2.0 ** retry_count, 60.0)
