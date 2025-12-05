#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RateLimitRegistry - API限流注册表

核心设计：
- 限流对象是API，不是data_type
- 统一管理所有API的限流器
- 支持Provider注册自己的API限流
"""

import time
import threading
from typing import Dict, Optional, List
from loguru import logger


class APIRateLimiter:
    """
    单个API的限流器（令牌桶算法）
    
    ⭐ 线程安全
    """
    
    def __init__(self, api_identifier: str, max_per_minute: int, buffer: int = 5):
        """
        初始化限流器
        
        Args:
            api_identifier: API唯一标识（如 'tushare.daily'）
            max_per_minute: 最大请求数/分钟
            buffer: 缓冲区大小（多线程环境需要更大）
        """
        self.api_identifier = api_identifier
        self.max_per_minute = max_per_minute
        self.buffer = buffer
        
        # 令牌桶
        self.tokens = max_per_minute
        self.last_update = time.time()
        
        # 线程锁
        self._lock = threading.Lock()
        
        # 统计
        self._request_count = 0
        self._throttle_count = 0
    
    def acquire(self, count: int = 1):
        """
        获取令牌（阻塞直到获得）
        
        Args:
            count: 需要的令牌数（默认1）
        """
        with self._lock:
            now = time.time()
            elapsed = now - self.last_update
            
            if elapsed > 0:
                # 补充令牌
                new_tokens = elapsed * (self.max_per_minute / 60.0)
                self.tokens = min(self.max_per_minute, self.tokens + new_tokens)
                self.last_update = now
            
            # 检查是否有足够的令牌
            if self.tokens >= count:
                self.tokens -= count
                self._request_count += count
                return
            
            # 没有足够的令牌，需要等待
            wait_time = (count - self.tokens) * (60.0 / self.max_per_minute)
            self._throttle_count += 1
            
            if self._throttle_count % 10 == 0:  # 每10次限流记录一次
                logger.warning(
                    f"⏰ API [{self.api_identifier}] 触发限流，"
                    f"等待 {wait_time:.2f}s（已限流 {self._throttle_count} 次）"
                )
        
        # 释放锁后等待（避免阻塞其他线程）
        time.sleep(wait_time)
        
        # 递归获取令牌
        self.acquire(count)
    
    def get_stats(self) -> Dict[str, int]:
        """
        获取统计信息
        
        Returns:
            Dict: 统计信息
        """
        with self._lock:
            return {
                'request_count': self._request_count,
                'throttle_count': self._throttle_count,
                'max_per_minute': self.max_per_minute
            }


class RateLimitRegistry:
    """
    API限流注册表
    
    ⭐ 关键设计：
    - 限流对象是API，不是data_type
    - 统一管理所有API的限流器
    - 支持Provider注册自己的API限流
    """
    
    def __init__(self):
        """初始化注册表"""
        self._limiters: Dict[str, APIRateLimiter] = {}
        self._lock = threading.Lock()
    
    def register_api(
        self, 
        api_identifier: str, 
        max_per_minute: int, 
        buffer: int = 5
    ):
        """
        注册API限流器
        
        Args:
            api_identifier: API唯一标识（如 'tushare.daily'）
            max_per_minute: 最大请求数/分钟
            buffer: 缓冲区大小
        """
        with self._lock:
            if api_identifier in self._limiters:
                logger.warning(f"⚠️  API [{api_identifier}] 已注册，跳过")
                return
            
            self._limiters[api_identifier] = APIRateLimiter(
                api_identifier=api_identifier,
                max_per_minute=max_per_minute,
                buffer=buffer
            )
            
            logger.info(
                f"✅ API [{api_identifier}] 限流器已注册：{max_per_minute}次/分钟"
            )
    
    def acquire(self, api_identifier: str, count: int = 1):
        """
        获取API令牌
        
        Args:
            api_identifier: API标识
            count: 需要的令牌数
        """
        if api_identifier not in self._limiters:
            logger.warning(
                f"⚠️  API [{api_identifier}] 未注册限流器，跳过限流"
            )
            return
        
        self._limiters[api_identifier].acquire(count)
    
    def get_limiter(self, api_identifier: str) -> Optional[APIRateLimiter]:
        """
        获取限流器实例
        
        Args:
            api_identifier: API标识
        
        Returns:
            APIRateLimiter: 限流器实例，如果不存在返回None
        """
        return self._limiters.get(api_identifier)
    
    def list_apis(self) -> List[str]:
        """
        列出所有已注册的API
        
        Returns:
            List[str]: API标识列表
        """
        with self._lock:
            return list(self._limiters.keys())
    
    def get_stats(self) -> Dict[str, Dict[str, int]]:
        """
        获取所有API的统计信息
        
        Returns:
            Dict: {api_identifier: stats}
        """
        with self._lock:
            return {
                api_id: limiter.get_stats()
                for api_id, limiter in self._limiters.items()
            }

