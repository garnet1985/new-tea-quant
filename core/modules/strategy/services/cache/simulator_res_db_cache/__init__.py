"""
策略 Simulator Res DB Cache：双指纹命中 ``sys_strategy_workbench_snapshot``，读写 ``reports`` / ``result_report``。

- **编排**（较重依赖）：``SimulatorResDbCacheService``、``lookup_enum_cache``、``persist_enum_snapshot`` — 首次访问 ``cache_service`` 时再加载。
- **对外门面**：``SimulatorResDbCacheWriteRequest``
- **指纹**：``finger_print`` 子包
- **枚举器适配器**：``enumerator_adapter``（枚举摘要写入快照前的规范化）
"""

from __future__ import annotations

from typing import Any

from core.modules.strategy.enums import Simulator

from . import config
from .enumerator_adapter import sanitize_enum_payload_for_snapshot
from .finger_print import (
    db_cache_fingerprint_pair,
    db_cache_fingerprint_pair_from_parts,
    semantic_core,
    settings_fingerprint_id,
    to_env_hash,
    to_settings_hash,
)
from .simulator_res_db_cache import SimulatorResDbCacheWriteRequest

_SERVICE_NAMES = frozenset(
    {
        "DbCacheService",
        "SimulatorResDbCacheService",
        "lookup_enum_cache",
        "persist_enum_snapshot",
    }
)

__all__ = [
    "DbCacheService",
    "Simulator",
    "SimulatorResDbCacheService",
    "SimulatorResDbCacheWriteRequest",
    "config",
    "sanitize_enum_payload_for_snapshot",
    "db_cache_fingerprint_pair",
    "db_cache_fingerprint_pair_from_parts",
    "lookup_enum_cache",
    "persist_enum_snapshot",
    "semantic_core",
    "settings_fingerprint_id",
    "to_env_hash",
    "to_settings_hash",
]


def __getattr__(name: str) -> Any:
    if name in _SERVICE_NAMES:
        from . import cache_service

        return getattr(cache_service, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(__all__) | _SERVICE_NAMES)
