"""
Discovery Module - 自动发现工具

提供通用的类、模块、配置自动发现功能。

使用场景：
- 自动发现 Provider 类
- 自动发现 Handler 类及其 Config
- 自动发现 Strategy Worker 类
- 自动发现 Adapter 类
- 自动发现 Schema 定义
"""

from .class_discovery import (
    ClassDiscovery,
    DiscoveryConfig,
    DiscoveryResult,
    discover_subclasses
)
from .module_discovery import ModuleDiscovery

__all__ = [
    'ClassDiscovery',
    'DiscoveryConfig',
    'DiscoveryResult',
    'ModuleDiscovery',
    'discover_subclasses',
]
