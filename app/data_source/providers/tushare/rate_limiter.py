#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tushare API 限流器
"""

import time
import threading
from typing import Optional, Dict, Any
from loguru import logger


class APIRateLimiter:
    """通用的API限流器"""
    
    def __init__(self, max_per_minute: int, api_name: str, buffer: int = 20):
        """
        初始化限流器
        
        Args:
            max_per_minute: 每分钟最大请求数
            api_name: API名称，用于日志
            buffer: 缓冲次数，避免达到硬限制
        """
        self.max_per_minute = max_per_minute
        self.actual_limit = max_per_minute - buffer
        self.api_name = api_name
        self.buffer = buffer
        
        # 计数器
        self.request_count = 0
        self.last_reset_time = 0
        
        # 线程锁
        self.lock = threading.Lock()
    
    def acquire(self) -> None:
        """
        获取API调用许可
        
        如果达到限制，会阻塞等待直到下一分钟
        """
        with self.lock:
            current_time = time.time()
            
            # 检查是否需要重置计数器（每分钟重置一次）
            if current_time - self.last_reset_time >= 60:
                self.request_count = 0
                self.last_reset_time = current_time
            
            # 如果当前分钟内的请求数已达到限制，则等待到下一分钟
            if self.request_count >= self.actual_limit:
                wait_time = 60 - (current_time - self.last_reset_time)
                if wait_time > 0:
                    logger.info(f"Tushare {self.api_name}API: 当前分钟已调用 {self.request_count} 次，为防止供应商API限流，等待 {wait_time:.1f} 秒到下一分钟...")
                    time.sleep(wait_time)
                    self.request_count = 0
                    self.last_reset_time = time.time()
            
            # 增加请求计数
            self.request_count += 1
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取当前限流器状态
        
        Returns:
            包含当前状态的字典
        """
        with self.lock:
            current_time = time.time()
            time_since_reset = current_time - self.last_reset_time
            
            return {
                'api_name': self.api_name,
                'request_count': self.request_count,
                'actual_limit': self.actual_limit,
                'max_per_minute': self.max_per_minute,
                'time_since_reset': time_since_reset,
                'remaining_requests': max(0, self.actual_limit - self.request_count),
                'next_reset_in': max(0, 60 - time_since_reset)
            }


class RateLimiterManager:
    """限流器管理器"""
    
    def __init__(self):
        """初始化限流器管理器"""
        self.limiters: Dict[str, APIRateLimiter] = {}
        self._lock = threading.Lock()
    
    def get_limiter(self, api_name: str, max_per_minute: int, buffer: int = 20) -> APIRateLimiter:
        """
        获取或创建限流器
        
        Args:
            api_name: API名称
            max_per_minute: 每分钟最大请求数
            buffer: 缓冲次数
            
        Returns:
            APIRateLimiter实例
        """
        with self._lock:
            if api_name not in self.limiters:
                self.limiters[api_name] = APIRateLimiter(max_per_minute, api_name, buffer)
            return self.limiters[api_name]
    
    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有限流器的状态
        
        Returns:
            所有限流器状态的字典
        """
        return {name: limiter.get_status() for name, limiter in self.limiters.items()}
