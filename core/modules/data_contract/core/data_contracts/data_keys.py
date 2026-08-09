"""Data Keys Registry（数据契约键值注册表）。

设计理念：
- 使用类属性常量，IDE 友好且避免拼写错误
- 系统与用户分别定义 data_keys；discovery 时合并进可用 key 集
- 对外合并视图：``contracts.DATA_KEY``（包装 ``SYS_DATA_KEY`` + 用户侧）

使用方式::

    from core.modules.data_contract import ContractIssuer
    from core.modules.data_contract.contracts import DATA_KEY

    contract = ContractIssuer.issue(DATA_KEY.STOCK_LIST)

    # declaration 中使用常量，避免硬编码字符串
    meta = {"key": SYS_DATA_KEY.STOCK_LIST, ...}

新增系统 contract：
1. ``core/data_contracts/<key>/declaration.py`` + ``loader.py``
2. 在本文件 ``SYS_DATA_KEY`` 增加常量
3. declaration 的 ``meta.key`` 使用该常量

用户扩展：在 userspace 定义 ``USER_DATA_KEY``，并提供对应 declaration/loader；
未在 USER_DATA_KEY 注册的 key，discovery 会报错并提示补常量。
"""

class SYS_DATA_KEY:
    """系统内置数据键值（枚举常量）。"""
    
    # Stock 相关
    STOCK_LIST = "stock.list"                    # 股票列表（全局）
    STOCK_KLINE_DAILY = "stock.kline.daily"     # 日K线（per_entity）
    STOCK_KLINE_WEEKLY = "stock.kline.weekly"   # 周K线（per_entity）
    STOCK_KLINE_MONTHLY = "stock.kline.monthly" # 月K线（per_entity）
    STOCK_FINANCE_QUARTERLY = "stock.finance.quarterly" # 季度财务数据（per_entity）
    STOCK_INDICATORS_DAILY = "stock.indicators.daily" # 日指标数据（per_entity）
    STOCK_ADJ_FACTOR_EVENTLOG = "stock.adj_factor.eventlog" # 复权因子（per_entity）
    STOCK_MONEYFLOW_DAILY = "stock.moneyflow.daily" # 资金流向（per_entity）
    STOCK_ST_PERIODS = "stock.st_periods"           # ST/*ST 警示时段（per_entity）
    
    # Index 相关
    INDEX_LIST = "index.list"                    # 指数列表（全局）
    INDEX_KLINE_DAILY = "index.kline.daily"     # 日K线（per_entity）
    INDEX_WEIGHT_DAILY = "index.weight.daily"   # 权重数据（per_entity）
    
    # Trade Calendar
    TRADE_CALENDAR = "trade.calendar"            # 交易日历（全局）
    
    # Macro 相关（全局）
    MACRO_GDP = "macro.gdp"                     # GDP数据
    MACRO_CPI = "macro.cpi"                     # CPI数据
    MACRO_PPI = "macro.ppi"                     # PPI数据
    MACRO_PMI = "macro.pmi"                     # PMI数据
    MACRO_LPR = "macro.lpr"                     # LPR数据
    MACRO_SHIBOR = "macro.shibor"               # Shibor数据
    
    # Tag
    TAG = "tag"                                 # 标签数据（全局）
    
    @classmethod
    def all_keys(cls) -> list:
        """返回所有系统 key（字符串列表）。"""
        return [
            cls.STOCK_LIST,
            cls.STOCK_KLINE_DAILY,
            cls.STOCK_KLINE_WEEKLY,
            cls.STOCK_KLINE_MONTHLY,
            cls.STOCK_FINANCE_QUARTERLY,
            cls.STOCK_INDICATORS_DAILY,
            cls.STOCK_ADJ_FACTOR_EVENTLOG,
            cls.STOCK_MONEYFLOW_DAILY,
            cls.STOCK_ST_PERIODS,
            cls.INDEX_LIST,
            cls.INDEX_KLINE_DAILY,
            cls.INDEX_WEIGHT_DAILY,
            cls.TRADE_CALENDAR,
            cls.MACRO_GDP,
            cls.MACRO_CPI,
            cls.MACRO_PPI,
            cls.MACRO_PMI,
            cls.MACRO_LPR,
            cls.MACRO_SHIBOR,
            cls.TAG,
        ]

__all__ = ['SYS_DATA_KEY']