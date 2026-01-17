"""
Handler 配置定义

采用"一个基类"的设计方式：BaseHandlerConfig 包含所有选项，学习成本最低。

设计原则：
1. 所有选项都在 BaseHandlerConfig 中（基础选项 + rolling 选项 + simple_api 选项）
2. 用户只需要继承 BaseHandlerConfig，定义自己业务相关的字段
3. 学习成本最低：用户不需要知道不同基类的区别、自动选择逻辑、配置冲突检测

字段说明：
- 基础选项：所有 Handler 都可以使用
- rolling 相关选项：适用于 RollingHandler（如 rolling_periods, rolling_months）
- simple_api 相关选项：适用于 SimpleApiHandler（如 method, provider_name）
- 用户可以根据需要选择使用相关选项

注意：
- Config 类是可选的，如果用户不需要类型安全，可以直接使用 mapping.json 中的字典
- 如果用户定义了 Config 类，mapping.json 中的 handler_config 会覆盖 Config 类的默认值

使用方式（可选）：
1. 在 Handler 模块中定义自己的 Config 类（继承 BaseHandlerConfig）
2. 定义自己业务相关的字段
3. 在 Handler 类中设置 config_class 属性指向该 Config 类
4. 框架会自动发现并使用该 Config 类

示例：
    # userspace/data_source/handlers/kline/config.py
    from core.modules.data_source.definition.handler_config import BaseHandlerConfig
    from dataclasses import dataclass
    from typing import Optional
    
    @dataclass
    class KlineHandlerConfig(BaseHandlerConfig):
        # 只需要定义业务相关的字段
        debug_limit_stocks: Optional[int] = None
        # 其他选项（如 rolling_periods）也在 BaseHandlerConfig 中，可以根据需要使用
    
    # userspace/data_source/handlers/kline/handler.py
    from .config import KlineHandlerConfig
    
    class KlineHandler(BaseDataSourceHandler):
        config_class = KlineHandlerConfig  # 可选：如果不定义，直接使用 mapping.json 中的字典
        ...
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Callable


@dataclass
class BaseHandlerConfig:
    """
    Handler 配置基类
    
    包含所有 Handler 配置选项（基础 + rolling + simple_api）。
    学习成本最低：用户只需要继承此类，定义自己业务相关的字段即可。
    
    字段说明：
    - 基础选项：所有 Handler 都可以使用
    - rolling 相关选项：适用于 RollingHandler（如 rolling_periods, rolling_months, date_format）
    - simple_api 相关选项：适用于 SimpleApiHandler（如 method, provider_name）
    - 用户可以根据需要选择使用相关选项
    
    注意：
    - Config 类是可选的，如果用户不需要类型安全，可以直接使用 mapping.json 中的字典
    - 如果用户定义了 Config 类，mapping.json 中的 handler_config 会覆盖 Config 类的默认值
    """
    # ========== Rolling/SimpleApi 通用选项 ==========
    # 注意：这些选项适用于 RollingHandler 和 SimpleApiHandler
    # 业务相关的字段应该在用户的 Config 类中定义
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
