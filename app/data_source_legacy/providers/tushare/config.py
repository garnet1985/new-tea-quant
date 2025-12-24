#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tushare API 配置管理
"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class APIRateLimit:
    """API限流配置"""
    max_per_minute: int
    buffer: int = 20  # 缓冲次数，避免达到硬限制
    
    @property
    def actual_limit(self) -> int:
        """实际使用的限制次数"""
        return self.max_per_minute - self.buffer


@dataclass
class WorkerConfig:
    """工作线程配置"""
    workers: int  # 工作线程数量
    timeout: float  # 秒
    execution_mode: str = "PARALLEL"


@dataclass
class TushareConfig:
    """Tushare API 统一配置"""
    
    # Token配置
    auth_token_file = 'app/data_source/providers/tushare/auth/token.txt'
    
    # 市场日历设置
    latest_market_open_day_backward_checking_days = 15
    
    # API限流配置
    kline_rate_limit = APIRateLimit(max_per_minute=800, buffer=20)  # 780次/分钟
    corp_finance_rate_limit = APIRateLimit(max_per_minute=500, buffer=20)  # 480次/分钟
    
    # 工作线程配置
    kline_worker = WorkerConfig(workers=5, timeout=3600.0)  # 1小时
    corp_finance_worker = WorkerConfig(workers=5, timeout=3600.0)  # 1小时
    
    # 进度显示配置
    progress_update_interval = 1  # 每完成1个任务更新进度
    progress_show_details = True  # 显示详细信息
    
    # 数据库配置
    enable_thread_safety = True
    use_connection_pool = True
    
    @classmethod
    def get_kline_config(cls) -> Dict[str, Any]:
        """获取K线数据相关配置"""
        return {
            'rate_limit': cls.kline_rate_limit,
            'worker': cls.kline_worker,
            'api_name': 'K线数据'
        }
    
    @classmethod
    def get_corp_finance_config(cls) -> Dict[str, Any]:
        """获取企业财务数据相关配置"""
        return {
            'rate_limit': cls.corp_finance_rate_limit,
            'worker': cls.corp_finance_worker,
            'api_name': '企业财务数据'
        }
