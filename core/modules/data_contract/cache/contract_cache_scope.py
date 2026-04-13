#!/usr/bin/env python3
"""Contract 缓存作用域：决定条目落在 global 还是 per-strategy Store。"""

from __future__ import annotations

from enum import Enum


class ContractCacheScope(str, Enum):
    """
    缓存层级 / 作用域（与 data contract 的 ``ContractScope`` 不同：这里只描述**缓存放哪一类 Store**）。

    非 ``NONE`` 时由 ``ContractCacheManager`` 分发到 ``GlobalContractCacheStore`` 或 ``PerStrategyContractCacheStore``。
    """

    GLOBAL = "global"
    """跨策略、进程内复用（对应 contract：GLOBAL + 非时序）。"""

    PER_STRATEGY = "per_strategy"
    """单次 scan/simulate（对应 contract：GLOBAL + 时序）。"""

    NONE = "none"
    """不由本组件两类 Store 管理（如 PER_ENTITY）。"""
