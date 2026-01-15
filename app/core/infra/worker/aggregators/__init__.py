"""
聚合器模块

提供多种聚合实现：
- SimpleAggregator: 简单聚合器
"""

from .base import Aggregator
from .simple_aggregator import SimpleAggregator

__all__ = [
    'Aggregator',
    'SimpleAggregator',
]
