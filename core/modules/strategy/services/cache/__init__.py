#!/usr/bin/env python3
"""
策略模块内与「缓存」相关的聚合导出。

- **DbCache（工作台快照表）**：``lookup_enum_cache`` / ``persist_enum_snapshot``（惰性加载 ``cache_service``，首次调用再拉取较重依赖）。
- **枚举摘要整形**：``sanitize_enum_payload_for_snapshot``（``snapshot_slot_adapters``）。
- **校验快照**：``validated_normalized_snapshot``（指纹侧 ``settings_resolver``）。

其它名字里带 cache、但不在本包的内容（数据契约、扫描 CSV、DataManager DbCache 等）见各子模块文档。
"""

from __future__ import annotations

from typing import Any

from .simulator_res_db_cache.snapshot_slot_adapters import sanitize_enum_payload_for_snapshot


def __getattr__(name: str) -> Any:
    if name == "persist_enum_snapshot":
        from .simulator_res_db_cache.snapshot_slot_adapters import persist_enum_snapshot

        return persist_enum_snapshot
    if name == "lookup_enum_cache":
        from .simulator_res_db_cache.snapshot_slot_adapters import lookup_enum_cache

        return lookup_enum_cache
    if name == "validated_normalized_snapshot":
        from .simulator_res_db_cache.finger_print.settings_resolver import validated_normalized_snapshot

        return validated_normalized_snapshot
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(
        [
            "lookup_enum_cache",
            "persist_enum_snapshot",
            "sanitize_enum_payload_for_snapshot",
            "validated_normalized_snapshot",
        ]
    )


__all__ = [
    "lookup_enum_cache",
    "persist_enum_snapshot",
    "sanitize_enum_payload_for_snapshot",
    "validated_normalized_snapshot",
]
