#!/usr/bin/env python3
"""
策略模块内与「缓存」相关的入口（本包 + 其它路径一览）。

**本包**
- ``persist_enum_snapshot`` / ``lookup_enum_cache`` — 惰性导出（薄封装在 ``simulator_res_db_cache.cache_service``，逻辑在 ``SimulatorResDbCacheService`` 私有方法）。
- 枚举载荷变换符号 — 自 ``simulator_res_db_cache.enumerator`` 再导出，便于与 enumerator 同路径导入。

**DbCache（回测快照表）**：请优先 ``from core.modules.strategy.services.cache.simulator_res_db_cache import DbCacheService``。

**校验快照**：``simulator_res_db_cache.finger_print.settings_resolver.validated_normalized_snapshot``（或经 ``services.cache`` 惰性导出）。

**策略模块内其它名字里带 cache、但不在本包的内容（刻意分域）**
- ``core.modules.data_contract.cache.ContractCacheManager`` — K 线/合约数据缓存。
- ``engines/scanner/helpers/cache_manager.py`` — 扫描 CSV 缓存。
- ``services/data/output/service.py`` — 输出读取内存缓存。
- ``enumerator`` 流程里的 ``global_extra_cache`` — 单次 run 预载。
- ``core.modules.data_manager...DbCacheService`` — 数据管理器的 DB 缓存（与策略 DbCache 无关）。

导入约定：枚举路径可使用 ``from core.modules.strategy.services.cache import lookup_enum_cache``。
"""

from __future__ import annotations

from typing import Any

from .simulator_res_db_cache.enumerator import (
    cached_storable_to_summary_row,
    load_enum_report_enrichment,
    resolve_enum_output_dir,
    sanitize_enum_payload_for_snapshot,
    summary_row_to_storable_enum_payload,
)


def __getattr__(name: str) -> Any:
    if name == "persist_enum_snapshot":
        from .simulator_res_db_cache.cache_service import persist_enum_snapshot

        return persist_enum_snapshot
    if name == "lookup_enum_cache":
        from .simulator_res_db_cache.cache_service import lookup_enum_cache

        return lookup_enum_cache
    if name == "validated_normalized_snapshot":
        from .simulator_res_db_cache.finger_print.settings_resolver import validated_normalized_snapshot

        return validated_normalized_snapshot
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    base = [
        "cached_storable_to_summary_row",
        "load_enum_report_enrichment",
        "lookup_enum_cache",
        "persist_enum_snapshot",
        "resolve_enum_output_dir",
        "sanitize_enum_payload_for_snapshot",
        "summary_row_to_storable_enum_payload",
        "validated_normalized_snapshot",
    ]
    return sorted(base)


__all__ = [
    "cached_storable_to_summary_row",
    "load_enum_report_enrichment",
    "lookup_enum_cache",
    "persist_enum_snapshot",
    "resolve_enum_output_dir",
    "sanitize_enum_payload_for_snapshot",
    "summary_row_to_storable_enum_payload",
    "validated_normalized_snapshot",
]
