"""
Data contract module — 新的实现（meta/runtime/specific 三层结构）。

使用方式：
    from core.modules.data_contract import ContractPool
    
    pool = ContractPool()
    pool.discover()
    contract = pool.get_contract("stock.kline.daily")
    contract.fill_in_data(runtime={...})
"""

from core.modules.data_contract.core.discovery.contract_pool import ContractPool

__all__ = ["ContractPool"]
