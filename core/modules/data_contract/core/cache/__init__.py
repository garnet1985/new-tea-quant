#!/usr/bin/env python3
"""
Data contract 运行时缓存：按 mapping 将条目放入 global 或「单次 run」层。

业务（如 strategy）在合适边界调用 ``ContractCacheManager.enter_strategy_run`` /
``exit_strategy_run`` 清空 per-strategy 层。
"""

from .cache_entry import ContractCacheEntry
from .contract_cache_manager import ContractCacheManager
from .contract_cache_scope import ContractCacheScope
from .policy import resolve_cache_scope, resolve_cache_scope_for_data_key
from .stores import GlobalContractCacheStore, PerStrategyContractCacheStore

__all__ = [
    "ContractCacheEntry",
    "ContractCacheManager",
    "ContractCacheScope",
    "GlobalContractCacheStore",
    "PerStrategyContractCacheStore",
    "resolve_cache_scope",
    "resolve_cache_scope_for_data_key",
]
