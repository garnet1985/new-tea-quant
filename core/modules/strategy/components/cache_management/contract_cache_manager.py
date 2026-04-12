#!/usr/bin/env python3
"""
Contract 缓存编排：持有 global / per-strategy 两个 Store，并封装生命周期。

外部（如 ``StrategyManager``）只在「单次策略 run」的开始/结束调用
``enter_strategy_run`` / ``exit_strategy_run``；内部对 per-strategy 层做清空。
写入哪一层由 ``ContractCacheScope`` + ``put_for_scope`` 等决定。
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .cache_entry import ContractCacheEntry
from .contract_cache_scope import ContractCacheScope
from .stores import GlobalContractCacheStore, PerStrategyContractCacheStore


class ContractCacheManager:
    def __init__(self) -> None:
        self.global_store = GlobalContractCacheStore()
        self.per_strategy_store = PerStrategyContractCacheStore()

    # --- 生命周期：外部只负责在合适时机调用，内部只处理 per-strategy 清空 ---

    def enter_strategy_run(self) -> None:
        """单次策略 run 开始（可与 exit 对称调用，避免沿用上一次的 per-strategy 数据）。"""
        self.per_strategy_store.clear()

    def exit_strategy_run(self) -> None:
        """单次策略 run 结束，释放 per-strategy 内存。"""
        self.per_strategy_store.clear()

    def clear_global(self) -> None:
        """显式清空 global 层（如进程级重置）。"""
        self.global_store.clear()

    def clear_all(self) -> None:
        self.global_store.clear()
        self.per_strategy_store.clear()

    # --- 读写：按缓存 scope 分发（NONE 不写） ---

    def get(self, cache_scope: ContractCacheScope, key: str) -> Optional[ContractCacheEntry]:
        if cache_scope == ContractCacheScope.GLOBAL:
            return self.global_store.get(key)
        if cache_scope == ContractCacheScope.PER_STRATEGY:
            return self.per_strategy_store.get(key)
        return None

    def put_for_scope(
        self,
        cache_scope: ContractCacheScope,
        key: str,
        *,
        meta: Optional[Dict[str, Any]] = None,
        data: Any = None,
    ) -> None:
        if cache_scope == ContractCacheScope.NONE:
            return
        if cache_scope == ContractCacheScope.GLOBAL:
            self.global_store.put_data(key, meta=meta, data=data)
        elif cache_scope == ContractCacheScope.PER_STRATEGY:
            self.per_strategy_store.put_data(key, meta=meta, data=data)

    def put_entry(self, cache_scope: ContractCacheScope, key: str, entry: ContractCacheEntry) -> None:
        if cache_scope == ContractCacheScope.NONE:
            return
        if cache_scope == ContractCacheScope.GLOBAL:
            self.global_store.put(key, entry)
        elif cache_scope == ContractCacheScope.PER_STRATEGY:
            self.per_strategy_store.put(key, entry)
