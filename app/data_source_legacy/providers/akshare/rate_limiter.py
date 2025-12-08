#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AKShare API 限流器
基于Tushare的限流器实现，适配东方财富API
"""

import time
import threading
from typing import Optional, Dict, Any
from loguru import logger


class AKShareRateLimiter:
    """东方财富API限流器"""
    
    def __init__(self, max_per_minute: int = 60, api_name: str = "东方财富", buffer: int = 10):
        """
        初始化限流器
        
        Args:
            max_per_minute: 每分钟最大请求数（默认60次，保守估计）
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
        
        # logger.info(f"🚦 {self.api_name} API限流器初始化: {self.actual_limit}次/分钟 (缓冲{buffer}次)")
    
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
                    logger.info(f"🚦 {self.api_name} API: 当前分钟已调用 {self.request_count} 次，为防止API限流，等待 {wait_time:.1f} 秒到下一分钟...")
                    time.sleep(wait_time)
                    self.request_count = 0
                    self.last_reset_time = time.time()
            
            # 增加请求计数
            self.request_count += 1
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取限流器状态
        
        Returns:
            包含当前状态的字典
        """
        with self.lock:
            current_time = time.time()
            time_since_reset = current_time - self.last_reset_time
            
            return {
                'api_name': self.api_name,
                'max_per_minute': self.max_per_minute,
                'actual_limit': self.actual_limit,
                'current_count': self.request_count,
                'time_since_reset': time_since_reset,
                'remaining_requests': max(0, self.actual_limit - self.request_count),
                'next_reset_in': max(0, 60 - time_since_reset)
            }
    
    def reset(self) -> None:
        """手动重置计数器"""
        with self.lock:
            self.request_count = 0
            self.last_reset_time = time.time()
            logger.info(f"🔄 {self.api_name} API限流器已重置")


class AKShareConfig:
    """AKShare API 统一配置"""
    
    # API限流配置 - 只针对东方财富API
    kline_rate_limit = {
        'max_per_minute': 80,  # 东方财富K线数据API
        'buffer': 10,
        'api_name': '东方财富K线数据'
    }
    
    # 工作线程配置
    max_workers = 2  # 降低并发数，减少API压力
    
    # 进度显示配置
    progress_update_interval = 10  # 每完成10个任务更新进度
    
    @classmethod
    def get_kline_config(cls) -> Dict[str, Any]:
        """获取K线数据相关配置"""
        return {
            'rate_limit': cls.kline_rate_limit,
            'max_workers': cls.max_workers,
            'api_name': '东方财富K线数据'
        }


# 全局限流器实例
_kline_rate_limiter = None


def get_kline_rate_limiter() -> AKShareRateLimiter:
    """获取东方财富K线数据API限流器"""
    global _kline_rate_limiter
    if _kline_rate_limiter is None:
        config = AKShareConfig.get_kline_config()
        _kline_rate_limiter = AKShareRateLimiter(**config['rate_limit'])
    return _kline_rate_limiter


def reset_rate_limiter():
    """重置限流器"""
    global _kline_rate_limiter
    
    if _kline_rate_limiter:
        _kline_rate_limiter.reset()
    
    logger.info("🔄 东方财富API限流器已重置")
