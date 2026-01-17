"""
Handler 配置定义

采用"多个 Config 类"的设计方式：根据 renew_mode 自动选择对应的 Config 类。

设计原则：
1. BaseHandlerConfig: 包含所有公用属性（provider_name, method, date_format 等）
2. IncrementalConfig: 增量更新模式（从最新日期到当前）
3. RollingConfig: 滚动刷新模式（每次刷新最近 N 个时间单位）
4. RefreshConfig: 全量刷新模式（使用 default_date_range）
5. 根据 renew_mode 字段自动选择对应的 Config 类

字段说明：
- BaseHandlerConfig: 公用属性（所有 Config 类都继承）
- IncrementalConfig: + table_name, date_field
- RollingConfig: + rolling_unit, rolling_length, table_name, date_field
- RefreshConfig: + default_date_range（不需要 table_name 和 date_field）

注意：
- Config 类是可选的，如果用户不需要类型安全，可以直接使用 mapping.json 中的字典
- 如果用户定义了 Config 类，mapping.json 中的 handler_config 会覆盖 Config 类的默认值
- renew_mode 必须显式声明，不声明就报错拒绝执行

使用方式（可选）：
1. 在 Handler 模块中定义自己的 Config 类（继承 IncrementalConfig/RollingConfig/RefreshConfig）
2. 定义自己业务相关的字段
3. 在 Handler 类中设置 config_class 属性指向该 Config 类
4. 框架会自动发现并使用该 Config 类

示例：
    # userspace/data_source/handlers/kline/config.py
    from core.modules.data_source.data_classes.handler_config import IncrementalConfig
    from dataclasses import dataclass
    from typing import Optional
    
    @dataclass
    class KlineHandlerConfig(IncrementalConfig):
        # 只需要定义业务相关的字段
        debug_limit_stocks: Optional[int] = None
    
    # userspace/data_source/handlers/kline/handler.py
    from .config import KlineHandlerConfig
    
    class KlineHandler(BaseDataSourceHandler):
        config_class = KlineHandlerConfig  # 可选：如果不定义，直接使用 mapping.json 中的字典
        ...
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Callable

from core.global_enums.enums import TimeUnit, UpdateMode


@dataclass
class BaseHandlerConfig:
    """
    Handler 配置基类
    
    包含所有 Handler 配置的公用属性。
    
    字段说明：
    - 基础选项：所有 Handler 都可以使用
    - Renew Mode 相关选项：数据更新模式
      - renew_mode: 更新模式（refresh | incremental | rolling）
      - date_format: 日期格式（quarter | month | date | none）
      - default_date_range: 默认日期范围（全量刷新或数据库为空时使用）
    - API 相关：provider_name, method, requires_date_range
    
    注意：
    - Config 类是可选的，如果用户不需要类型安全，可以直接使用 mapping.json 中的字典
    - 如果用户定义了 Config 类，mapping.json 中的 handler_config 会覆盖 Config 类的默认值
    """
    # ========== 基础选项 ==========
    requires_date_range: bool = True  # 是否需要日期范围
    
    # ========== API 配置（字典格式：name -> 配置）==========
    apis: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    # 格式：{"api_name": {"provider_name": "tushare", "method": "get_data", "field_mapping": {...}, ...}}
    # 示例：
    # {
    #     "finance_data": {
    #         "provider_name": "tushare",
    #         "method": "get_finance_data",
    #         "api_name": "get_finance_data",
    #         "field_mapping": {"id": "ts_code", "date": "quarter"},
    #         "params": {}
    #     }
    # }
    
    # ========== Renew Mode 相关选项（公用）==========
    # 注意：为了兼容配置文件（JSON），这里使用 str 类型，但值应该使用枚举值
    # 使用 UpdateMode.ROLLING.value 或 TimeUnit.DAY.value 来获取字符串值
    renew_mode: str = UpdateMode.ROLLING.value  # 更新模式：refresh | incremental | rolling（必须显式声明）
    date_format: str = TimeUnit.DAY.value  # 日期格式：quarter | month | day | none
    default_date_range: Dict[str, int] = field(default_factory=dict)  # 默认日期范围（如 {"years": 5}）
    
    # ========== 测试相关选项 ==========
    dry_run: bool = False  # 干运行模式：如果为 True，不写入任何数据（用于测试）
    test_mode: bool = False  # 测试模式：如果为 True，只处理少量数据（用于测试）
    
    # ========== 自定义逻辑（可选）==========
    custom_before_fetch: Optional[Callable] = None  # 自定义 before_fetch 逻辑
    custom_normalize: Optional[Callable] = None  # 自定义 normalize 逻辑


@dataclass
class IncrementalConfig(BaseHandlerConfig):
    """
    增量更新模式配置
    
    从最新日期到当前（incremental）。
    如果数据库为空，使用 default_date_range 作为 fallback。
    
    字段说明：
    - 继承 BaseHandlerConfig 的所有字段
    - table_name: 数据库表名（用于查询最新日期）
    - date_field: 数据库日期字段名（用于查询最新日期）
    """
    table_name: Optional[str] = None  # 数据库表名（用于查询最新日期）
    date_field: Optional[str] = None  # 数据库日期字段名（用于查询最新日期）
    
    def __post_init__(self):
        """验证配置"""
        if self.renew_mode != UpdateMode.INCREMENTAL.value:
            raise ValueError(f"IncrementalConfig 的 renew_mode 必须是 '{UpdateMode.INCREMENTAL.value}'，当前值: {self.renew_mode}")
        if not self.table_name:
            raise ValueError("IncrementalConfig 必须提供 table_name")
        if not self.date_field:
            raise ValueError("IncrementalConfig 必须提供 date_field")


@dataclass
class RollingConfig(BaseHandlerConfig):
    """
    滚动刷新模式配置
    
    每次刷新最近 N 个时间单位（rolling）。
    需要滚动单位和每个滚动单位的长度。
    
    字段说明：
    - 继承 BaseHandlerConfig 的所有字段
    - rolling_unit: 滚动单位（"quarter" | "month" | "day"）
    - rolling_length: 每个滚动单位的长度（int，如 4 表示 4 个季度）
    - table_name: 数据库表名（用于查询最新日期）
    - date_field: 数据库日期字段名（用于查询最新日期）
    """
    rolling_unit: str = TimeUnit.DAY.value  # 滚动单位：quarter | month | day
    rolling_length: int = 30  # 每个滚动单位的长度（如 4 个季度、30 天）
    table_name: Optional[str] = None  # 数据库表名（用于查询最新日期）
    date_field: Optional[str] = None  # 数据库日期字段名（用于查询最新日期）
    
    def __post_init__(self):
        """验证配置"""
        if self.renew_mode != UpdateMode.ROLLING.value:
            raise ValueError(f"RollingConfig 的 renew_mode 必须是 '{UpdateMode.ROLLING.value}'，当前值: {self.renew_mode}")
        valid_units = [TimeUnit.QUARTER.value, TimeUnit.MONTH.value, TimeUnit.DAY.value]
        if self.rolling_unit not in valid_units:
            raise ValueError(f"RollingConfig 的 rolling_unit 必须是 '{TimeUnit.QUARTER.value}' | '{TimeUnit.MONTH.value}' | '{TimeUnit.DAY.value}'，当前值: {self.rolling_unit}")
        if self.rolling_length <= 0:
            raise ValueError(f"RollingConfig 的 rolling_length 必须是正整数，当前值: {self.rolling_length}")
        if not self.table_name:
            raise ValueError("RollingConfig 必须提供 table_name")
        if not self.date_field:
            raise ValueError("RollingConfig 必须提供 date_field")
        
        # 验证 rolling_unit 和 date_format 的一致性（建议，但不强制）
        if self.date_format == TimeUnit.QUARTER.value and self.rolling_unit != TimeUnit.QUARTER.value:
            # 只是警告，不报错
            import warnings
            warnings.warn(
                f"RollingConfig: date_format='{TimeUnit.QUARTER.value}' 但 rolling_unit='{self.rolling_unit}'，"
                f"建议保持一致"
            )


@dataclass
class RefreshConfig(BaseHandlerConfig):
    """
    全量刷新模式配置
    
    使用 default_date_range 进行全量刷新（refresh）。
    不需要查询数据库，所以不需要 table_name 和 date_field。
    
    字段说明：
    - 继承 BaseHandlerConfig 的所有字段
    - default_date_range: 默认日期范围（必需，用于全量刷新）
    """
    def __post_init__(self):
        """验证配置"""
        if self.renew_mode != UpdateMode.REFRESH.value:
            raise ValueError(f"RefreshConfig 的 renew_mode 必须是 '{UpdateMode.REFRESH.value}'，当前值: {self.renew_mode}")
        if not self.default_date_range and self.date_format != TimeUnit.NONE.value:
            # 警告，但不强制（有些 handler 可能不需要日期范围）
            # 如果 date_format 是 "none"，则不需要日期范围，不警告
            import warnings
            warnings.warn(
                "RefreshConfig: default_date_range 为空，全量刷新可能无法确定日期范围"
            )
