"""
DataSource Data Classes 模块

提供标准化的 DataSource 配置对象和数据类，用于统一管理 DataSource 的配置和执行。
"""
from .handler_config import (
    BaseHandlerConfig,
    IncrementalConfig,
    RollingConfig,
    RefreshConfig,
)
from .data_source_definition import DataSourceDefinition
from .api_job import ApiJob
from .data_source_task import DataSourceTask

__all__ = [
    # Handler 配置
    "BaseHandlerConfig",
    "IncrementalConfig",
    "RollingConfig",
    "RefreshConfig",
    # 核心定义
    "DataSourceDefinition",
    # API 和 Task
    "ApiJob",
    "DataSourceTask",
]
