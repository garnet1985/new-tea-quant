#!/usr/bin/env python3
"""两类 Store：global（跨策略）与 per-strategy（单次 run）。"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .cache_entry import ContractCacheEntry


class GlobalContractCacheStore:
    """跨策略、进程内保留的 contract 缓存（如 GLOBAL 非时序）。"""

    def __init__(self) -> None:
        self._entries: Dict[str, ContractCacheEntry] = {}

    def get(self, key: str) -> Optional[ContractCacheEntry]:
        return self._entries.get(key)

    def put(self, key: str, entry: ContractCacheEntry) -> None:
        self._entries[key] = entry

    def put_data(
        self,
        key: str,
        *,
        meta: Optional[Dict[str, Any]] = None,
        data: Any = None,
    ) -> None:
        self._entries[key] = ContractCacheEntry(meta=dict(meta or {}), data=data)

    def clear(self) -> None:
        self._entries.clear()


class PerStrategyContractCacheStore:
    """绑定单次 scan/simulate；由 ``ContractCacheManager`` 在 run 边界清空。"""

    def __init__(self) -> None:
        self._entries: Dict[str, ContractCacheEntry] = {}

    def get(self, key: str) -> Optional[ContractCacheEntry]:
        return self._entries.get(key)

    def put(self, key: str, entry: ContractCacheEntry) -> None:
        self._entries[key] = entry

    def put_data(
        self,
        key: str,
        *,
        meta: Optional[Dict[str, Any]] = None,
        data: Any = None,
    ) -> None:
        self._entries[key] = ContractCacheEntry(meta=dict(meta or {}), data=data)

    def clear(self) -> None:
        self._entries.clear()
