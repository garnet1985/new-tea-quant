"""
策略 Simulator Res DB Cache：双指纹命中 ``sys_strategy_workbench_snapshot``，读写 ``reports`` / ``result_report``。

- **表服务**：``SimulatorResDbCacheService``（``cache_service``）
- **槽位与枚举载荷**：``snapshot_slot_adapters``（lookup / persist + ``sanitize_enum_payload_for_snapshot``）
- **指纹输入**：``helpers.db_cache_run_inputs``（flow 与 env 指纹对齐）
- **对外门面**：``SimulatorResDbCacheWriteRequest``
- **指纹**：``finger_print`` 子包
"""

from __future__ import annotations

from typing import Any

from core.modules.strategy.enums import Simulator

from . import config
from .snapshot_slot_adapters import sanitize_enum_payload_for_snapshot
from .finger_print import (
    db_cache_fingerprint_pair,
    db_cache_fingerprint_pair_from_parts,
    semantic_core,
    settings_fingerprint_id,
    to_env_hash,
    to_settings_hash,
)
from .simulator_res_db_cache import SimulatorResDbCacheWriteRequest

_CACHE_SERVICE_NAMES = frozenset({"DbCacheService", "SimulatorResDbCacheService"})
_SNAPSHOT_SLOT_NAMES = frozenset(
    {
        "lookup_capital_allocation_cache",
        "lookup_enum_cache",
        "lookup_price_factor_cache",
        "persist_capital_allocation_snapshot",
        "persist_enum_snapshot",
        "persist_price_factor_snapshot",
    }
)
_LAZY_NAMES = _CACHE_SERVICE_NAMES | _SNAPSHOT_SLOT_NAMES

__all__ = [
    "DbCacheService",
    "Simulator",
    "SimulatorResDbCacheService",
    "SimulatorResDbCacheWriteRequest",
    "config",
    "sanitize_enum_payload_for_snapshot",
    "db_cache_fingerprint_pair",
    "db_cache_fingerprint_pair_from_parts",
    "lookup_capital_allocation_cache",
    "lookup_enum_cache",
    "lookup_price_factor_cache",
    "persist_capital_allocation_snapshot",
    "persist_enum_snapshot",
    "persist_price_factor_snapshot",
    "semantic_core",
    "settings_fingerprint_id",
    "to_env_hash",
    "to_settings_hash",
]


def __getattr__(name: str) -> Any:
    if name in _CACHE_SERVICE_NAMES:
        from . import cache_service

        return getattr(cache_service, name)
    if name in _SNAPSHOT_SLOT_NAMES:
        from . import snapshot_slot_adapters

        return getattr(snapshot_slot_adapters, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(__all__) | _LAZY_NAMES)
