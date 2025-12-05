"""
Data Provider 模块

统一管理所有数据源（Tushare、AKShare等）

核心特性：
- 统一接口（BaseProvider）
- 声明式依赖（自动协调）
- API级别限流（智能并发）
- 动态挂载（零硬编码）
"""

__version__ = '2.0.0'
__author__ = 'garnet'

# TODO: Phase 1 实施后取消注释
# from .core.base_provider import BaseProvider, ProviderInfo, Dependency, ExecutionContext
# from .core.provider_registry import ProviderRegistry
# from .core.rate_limit_registry import RateLimitRegistry
# from .core.data_coordinator import DataCoordinator

# __all__ = [
#     'BaseProvider',
#     'ProviderInfo',
#     'Dependency',
#     'ExecutionContext',
#     'ProviderRegistry',
#     'RateLimitRegistry',
#     'DataCoordinator',
# ]

