"""
DataSource Definition 模块

提供标准化的 DataSource 配置对象，用于统一管理 DataSource 的配置。
"""
from .api_config import ApiConfig, ProviderConfig
from .handler_config import BaseHandlerConfig
from .data_source_definition import DataSourceDefinition

__all__ = [
    # API 配置
    "ApiConfig",
    "ProviderConfig",
    # Handler 配置（所有选项都在 BaseHandlerConfig 中）
    "BaseHandlerConfig",
    # 核心定义
    "DataSourceDefinition",
]
