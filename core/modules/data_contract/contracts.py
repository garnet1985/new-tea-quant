"""Data contract public types — classes only (cross-module import entry).

新实现导出（meta/runtime/specific 三层结构）：
- ContractIssuer：发现和管理 contract（包根 Facade re-export）
- BaseDataContract：基类（meta/runtime/specific）
- DATA_KEY / SYS_DATA_KEY：契约键值常量

使用方式::

    from core.modules.data_contract import ContractIssuer
    from core.modules.data_contract.contracts import DATA_KEY, BaseDataContract

    contract = ContractIssuer.issue(DATA_KEY.STOCK_LIST, fill_in_data=True)
    stock_list = contract.get_data()
"""

from core.modules.data_contract.core.discovery.contract_issuer import ContractIssuer

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
    CursorState,
)
from core.modules.data_contract.core.base.base_non_time_series_contract import (
    BaseNonTimeSeriesContract,
)
from core.modules.data_contract.core.base.base_loader import (
    BaseDataContractLoader,
)
from core.modules.data_contract.core.data_contracts.data_keys import SYS_DATA_KEY


class DATA_KEY:
    """数据契约键值（合并系统 + 用户）。

    系统 key（SYS_DATA_KEY）在 discovery 时自动合并；
    用户 key（USER_DATA_KEY）在 userspace/data_keys.py 中定义。
    """

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


__all__ = [
    # Discovery
    "ContractIssuer",

    # Data keys
    "SYS_DATA_KEY",
    "DATA_KEY",

    # Base classes
    "BaseDataContract",
    "ContractType",
    "ContractScope",
    "ContractMeta",
    "ContractRuntime",
    "ContractSpecific",

    # Time series contract
    "BaseTimeSeriesContract",
    "TimeRange",
    "CursorState",

    # Non time series contract
    "BaseNonTimeSeriesContract",

    # Loader
    "BaseDataContractLoader",
]