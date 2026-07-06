"""
Data contract module — 新的实现（meta/runtime/specific 三层结构）。

使用方式：
    from core.modules.data_contract import ContractIssuer
    
    issuer = ContractIssuer()
    issuer.discover()
    
    # 获取 contract
    contract = issuer.get_contract("stock.kline.daily")
    
    # 添加 runtime 并加载
    contract.fill_in_data(runtime={
        "entity_ids": ["600000.SH"],
        "start_time": "20200101",
        "end_time": "20201231",
        "adjust": "qfq",
    })
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

__all__ = [
    # Discovery
    "ContractIssuer",
    
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