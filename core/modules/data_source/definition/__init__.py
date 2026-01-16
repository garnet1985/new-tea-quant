"""
DataSource Definition 模块

提供标准化的 DataSource 配置对象，用于统一管理 DataSource 的配置。
"""
from .api_config import ApiConfig, ProviderConfig
from .handler_config import (
    BaseHandlerConfig,
    RollingHandlerConfig,
    KlineHandlerConfig,
    SimpleApiHandlerConfig,
    CorporateFinanceHandlerConfig,
    LatestTradingDateHandlerConfig,
    AdjFactorEventHandlerConfig,
    PriceIndexesHandlerConfig,
    StockIndexIndicatorHandlerConfig,
    StockIndexIndicatorWeightHandlerConfig,
    TushareStockListHandlerConfig,
    IndustryCapitalFlowHandlerConfig,
)
from .data_source_definition import DataSourceDefinition

__all__ = [
    # API 配置
    "ApiConfig",
    "ProviderConfig",
    # Handler 配置
    "BaseHandlerConfig",
    "RollingHandlerConfig",
    "KlineHandlerConfig",
    "SimpleApiHandlerConfig",
    "CorporateFinanceHandlerConfig",
    "LatestTradingDateHandlerConfig",
    "AdjFactorEventHandlerConfig",
    "PriceIndexesHandlerConfig",
    "StockIndexIndicatorHandlerConfig",
    "StockIndexIndicatorWeightHandlerConfig",
    "TushareStockListHandlerConfig",
    "IndustryCapitalFlowHandlerConfig",
    # 核心定义
    "DataSourceDefinition",
]
