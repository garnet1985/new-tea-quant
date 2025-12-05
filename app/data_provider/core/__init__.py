"""
Core 模块

核心组件：
- BaseProvider: 统一接口
- ProviderRegistry: 动态挂载
- RateLimitRegistry: API限流注册表
- DataCoordinator: 数据协调器
- SmartConcurrentExecutor: 智能并发执行器
"""

from .base_provider import (
    BaseProvider,
    ProviderInfo,
    Dependency,
    ExecutionContext
)

from .rate_limit_registry import (
    RateLimitRegistry,
    APIRateLimiter
)

from .provider_registry import (
    ProviderRegistry,
    ProviderMetadata
)

from .smart_concurrent import (
    SmartConcurrentExecutor
)

from .data_coordinator import (
    DataCoordinator,
    DependencyGraph
)

__all__ = [
    # BaseProvider
    'BaseProvider',
    'ProviderInfo',
    'Dependency',
    'ExecutionContext',
    
    # RateLimitRegistry
    'RateLimitRegistry',
    'APIRateLimiter',
    
    # ProviderRegistry
    'ProviderRegistry',
    'ProviderMetadata',
    
    # SmartConcurrentExecutor
    'SmartConcurrentExecutor',
    
    # DataCoordinator
    'DataCoordinator',
    'DependencyGraph',
]

