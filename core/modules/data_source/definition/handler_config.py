"""
Handler 配置定义

为每个 Handler 类型定义专门的 Config 类，提供类型安全和清晰的配置结构。
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Callable, List


@dataclass
class BaseHandlerConfig:
    """
    Handler 配置基类
    
    所有 Handler Config 都继承自此类。
    即使某个 Handler 没有特定参数，也应该定义对应的 Config 类（可以为空）。
    """
    pass


@dataclass
class RollingHandlerConfig(BaseHandlerConfig):
    """
    RollingHandler 配置
    
    用于滚动刷新 Handler 的配置。
    """
    provider_name: str = "tushare"  # Provider 名称（将被移到 ApiConfig）
    method: str = ""  # API 方法名（将被移到 ApiConfig）
    date_format: str = "date"  # 日期格式：quarter | month | date | none
    default_date_range: Dict[str, int] = field(default_factory=dict)  # 默认日期范围
    rolling_periods: Optional[int] = None  # 滚动刷新周期数
    rolling_months: Optional[int] = None  # 滚动刷新月数（替代 rolling_periods）
    table_name: Optional[str] = None  # 数据库表名
    date_field: Optional[str] = None  # 数据库日期字段名
    requires_date_range: bool = True  # 是否需要日期范围
    custom_before_fetch: Optional[Callable] = None  # 自定义 before_fetch 逻辑
    custom_normalize: Optional[Callable] = None  # 自定义 normalize 逻辑
    # 注意：field_mapping 应该在 ApiConfig 中配置，不在这里


@dataclass
class SimpleApiHandlerConfig(BaseHandlerConfig):
    """
    SimpleApiHandler 配置
    
    用于简单 API Handler 的配置。
    """
    provider_name: str = "tushare"  # Provider 名称（将被移到 ApiConfig）
    method: str = ""  # API 方法名（将被移到 ApiConfig）
    date_format: str = "date"  # 日期格式：quarter | month | date | none
    default_date_range: Dict[str, int] = field(default_factory=dict)  # 默认日期范围
    requires_date_range: bool = True  # 是否需要日期范围
    custom_before_fetch: Optional[Callable] = None  # 自定义 before_fetch 逻辑
    custom_normalize: Optional[Callable] = None  # 自定义 normalize 逻辑
    # 注意：field_mapping 应该在 ApiConfig 中配置，不在这里


@dataclass
class KlineHandlerConfig(BaseHandlerConfig):
    """
    KlineHandler 配置
    
    用于 K 线数据 Handler 的配置。
    """
    debug_limit_stocks: Optional[int] = None  # 调试模式：限制股票数量


@dataclass
class CorporateFinanceHandlerConfig(BaseHandlerConfig):
    """
    CorporateFinanceHandler 配置
    
    用于企业财务数据 Handler 的配置。
    """
    pass  # 目前没有特定参数


@dataclass
class LatestTradingDateHandlerConfig(BaseHandlerConfig):
    """
    LatestTradingDateHandler 配置
    
    用于最新交易日 Handler 的配置。
    """
    backward_checking_days: int = 15  # 向后检查天数


@dataclass
class AdjFactorEventHandlerConfig(BaseHandlerConfig):
    """
    AdjFactorEventHandler 配置
    
    用于复权因子事件 Handler 的配置。
    """
    update_threshold_days: int = 15  # 更新阈值天数
    max_workers: int = 10  # 最大工作线程数


@dataclass
class PriceIndexesHandlerConfig(BaseHandlerConfig):
    """
    PriceIndexesHandler 配置
    
    用于价格指数 Handler 的配置。
    """
    default_date_range: Dict[str, Any] = field(default_factory=dict)  # 默认日期范围
    rolling_months: Optional[int] = None  # 滚动刷新月数


@dataclass
class StockIndexIndicatorHandlerConfig(BaseHandlerConfig):
    """
    StockIndexIndicatorHandler 配置
    
    用于股票指数指标 Handler 的配置。
    """
    index_list: List[Dict[str, str]] = field(default_factory=list)  # 指数列表


@dataclass
class StockIndexIndicatorWeightHandlerConfig(BaseHandlerConfig):
    """
    StockIndexIndicatorWeightHandler 配置
    
    用于股票指数权重 Handler 的配置。
    """
    index_list: List[Dict[str, str]] = field(default_factory=list)  # 指数列表


@dataclass
class TushareStockListHandlerConfig(BaseHandlerConfig):
    """
    TushareStockListHandler 配置
    
    用于股票列表 Handler 的配置。
    """
    api_fields: str = "ts_code,symbol,name,area,industry,market,exchange,list_date"  # API 字段列表


@dataclass
class IndustryCapitalFlowHandlerConfig(BaseHandlerConfig):
    """
    IndustryCapitalFlowHandler 配置
    
    用于行业资金流向 Handler 的配置。
    """
    default_date_range: Dict[str, Any] = field(default_factory=dict)  # 默认日期范围
