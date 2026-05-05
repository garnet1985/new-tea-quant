"""
策略 **Simulator Res DB Cache**：指纹命中 ``sys_strategy_workbench_snapshot``，读写 ``result_report``。

- **入口**：``simulator_res_db_cache`` 模块内 ``read_cache`` / ``write_cache`` / ``apply_cache``
- **协调类**：``cache_service.SimulatorResDbCacheService``
- **指纹**：``finger_print``
- **版本展示字符串**（``v{n}``）：若保留 ``domain.snapshot_service``，供其它模块使用

``settings.StrategySettingsService``：API/runtime 形态与校验（如存在对应子包）。
"""

from __future__ import annotations

from . import config
from core.modules.strategy.enums import Simulator
from .finger_print import (
    db_cache_fingerprint_pair,
    db_cache_fingerprint_pair_from_parts,
    semantic_core,
    settings_fingerprint_id,
    to_env_hash,
    to_settings_hash,
)
from .cache_service import DbCacheService, SimulatorResDbCacheService
from .simulator_res_db_cache import EnumCacheResult, apply_cache, read_cache, write_cache

__all__ = [
    "DbCacheService",
    "EnumCacheResult",
    "Simulator",
    "SimulatorResDbCacheService",
    "apply_cache",
    "config",
    "db_cache_fingerprint_pair",
    "db_cache_fingerprint_pair_from_parts",
    "read_cache",
    "semantic_core",
    "settings_fingerprint_id",
    "to_env_hash",
    "to_settings_hash",
    "write_cache",
]
