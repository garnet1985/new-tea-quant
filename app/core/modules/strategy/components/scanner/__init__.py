#!/usr/bin/env python3
"""
Scanner 组件

职责：
- 日期解析（严格上一个交易日 vs 最新 K 线日期）
- 机会扫描（调用 BaseStrategyWorker.scan_opportunity）
- 结果缓存（CSV 持久化）
- Adapter 分发（console、webhook 等）
"""

from .scanner import Scanner
from .scan_date_resolver import ScanDateResolver
from .scan_cache_manager import ScanCacheManager
from .adapter_dispatcher import AdapterDispatcher

__all__ = [
    'Scanner',
    'ScanDateResolver',
    'ScanCacheManager',
    'AdapterDispatcher',
]
