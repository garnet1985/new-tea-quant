"""
Data contract module — 新的实现（meta/runtime/specific 三层结构）。

使用方式：
    from core.modules.data_contract import ContractIssuer, DATA_KEY
    
    # 方式1：静态方式（推荐）
    contract = ContractIssuer.issue(DATA_KEY.STOCK_LIST, fill_in_data=True)
    stock_list = contract.get_data()
    
    # 方式2：per_entity contract
    contract = ContractIssuer.issue(
        DATA_KEY.STOCK_KLINE_DAILY,
        entity_ids=["600000.SH"],
        runtime={
            "start_time": "20200101",
            "end_time": "20201231",
        },
        fill_in_data=True,
    )
    kline_data = contract.get_data()
"""

from core.modules.data_contract.core.discovery.contract_issuer import ContractIssuer

# 导出基类（供用户自定义 contract）
from core.modules.data_contract.core.base.base_contract import (
    BaseDataContract,
    ContractType,
    ContractScope,
    ContractMeta,
    ContractRuntime,
    ContractSpecific,
)
from core.modules.data_contract.core.base.base_time_series_contract import (
    BaseTimeSeriesContract,
    TimeRange,
)
from core.modules.data_contract.core.base.base_non_time_series_contract import (
    BaseNonTimeSeriesContract,
)
from core.modules.data_contract.core.base.base_loader import (
    BaseDataContractLoader,
)

# 导出 SYS_DATA_KEY（系统内置）
from core.modules.data_contract.core.data_contracts.data_keys import SYS_DATA_KEY

# 动态合并 DATA_KEY（SYS_DATA_KEY + USER_DATA_KEY）
# 在 discovery 时自动合并用户自定义的 USER_DATA_KEY
class DATA_KEY:
    """数据契约键值（合并系统 + 用户）。
    
    使用方式：
        from core.modules.data_contract import DATA_KEY
        contract = ContractIssuer.issue(DATA_KEY.STOCK_LIST)
        
        # declaration 中使用
        meta: {
            key: DATA_KEY.STOCK_LIST,
            ...
        }
    
    注意：
    - 系统 key（SYS_DATA_KEY）在 discovery 时自动合并
    - 用户 key（USER_DATA_KEY）需要用户在 userspace/data_keys.py 中定义
    """
    
    # 系统 key（硬编码，便于IDE自动补全）
    STOCK_LIST = SYS_DATA_KEY.STOCK_LIST
    STOCK_KLINE_DAILY = SYS_DATA_KEY.STOCK_KLINE_DAILY
    STOCK_KLINE_WEEKLY = SYS_DATA_KEY.STOCK_KLINE_WEEKLY
    STOCK_KLINE_MONTHLY = SYS_DATA_KEY.STOCK_KLINE_MONTHLY
    STOCK_FINANCE_QUARTERLY = SYS_DATA_KEY.STOCK_FINANCE_QUARTERLY
    STOCK_INDICATORS_DAILY = SYS_DATA_KEY.STOCK_INDICATORS_DAILY
    STOCK_ADJ_FACTOR_EVENTLOG = SYS_DATA_KEY.STOCK_ADJ_FACTOR_EVENTLOG
    STOCK_MONEYFLOW_DAILY = SYS_DATA_KEY.STOCK_MONEYFLOW_DAILY
    STOCK_ST_PERIODS = SYS_DATA_KEY.STOCK_ST_PERIODS
    
    INDEX_LIST = SYS_DATA_KEY.INDEX_LIST
    INDEX_KLINE_DAILY = SYS_DATA_KEY.INDEX_KLINE_DAILY
    INDEX_WEIGHT_DAILY = SYS_DATA_KEY.INDEX_WEIGHT_DAILY
    
    TRADE_CALENDAR = SYS_DATA_KEY.TRADE_CALENDAR
    
    MACRO_GDP = SYS_DATA_KEY.MACRO_GDP
    MACRO_CPI = SYS_DATA_KEY.MACRO_CPI
    MACRO_PPI = SYS_DATA_KEY.MACRO_PPI
    MACRO_PMI = SYS_DATA_KEY.MACRO_PMI
    MACRO_LPR = SYS_DATA_KEY.MACRO_LPR
    MACRO_SHIBOR = SYS_DATA_KEY.MACRO_SHIBOR
    
    TAG = SYS_DATA_KEY.TAG
    
    # 用户自定义 key（动态添加，在 discovery 时合并）
    # 注意：用户需要在 userspace/data_keys.py 中定义 USER_DATA_KEY 类


__all__ = [
    # Discovery
    "ContractIssuer",
    
    # Data Keys
    "SYS_DATA_KEY",
    "DATA_KEY",
    
    # Base classes（供用户自定义）
    "BaseDataContract",
    "ContractType",
    "ContractScope",
    "ContractMeta",
    "ContractRuntime",
    "ContractSpecific",
    
    # Time series contract
    "BaseTimeSeriesContract",
    "TimeRange",
    
    # Non time series contract
    "BaseNonTimeSeriesContract",
    
    # Loader
    "BaseDataContractLoader",
]