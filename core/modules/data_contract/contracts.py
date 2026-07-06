"""Data contract public types — classes only (cross-module import entry).

新实现导出（meta/runtime/specific 三层结构）：
- ContractIssuer：发现和管理 contract
- BaseDataContract：基类（meta/runtime/specific）
- BaseTimeSeriesContract：时序基类（扩展时间辅助工具）
- BaseNonTimeSeriesContract：非时序基类
- BaseDataContractLoader：loader 基类

使用方式：
    from core.modules.data_contract.contracts import (
        ContractIssuer,
        BaseDataContract,
        BaseTimeSeriesContract,
        ContractMeta,
        ContractRuntime,
    )
    
    issuer = ContractIssuer()
    issuer.discover()
    contract = issuer.get_contract("stock.kline.daily")
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
)
from core.modules.data_contract.core.base.base_non_time_series_contract import (
    BaseNonTimeSeriesContract,
)
from core.modules.data_contract.core.base.base_loader import (
    BaseDataContractLoader,
)

__all__ = [
    # Discovery
    "ContractIssuer",
    
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
    
    # Non time series contract
    "BaseNonTimeSeriesContract",
    
    # Loader
    "BaseDataContractLoader",
]