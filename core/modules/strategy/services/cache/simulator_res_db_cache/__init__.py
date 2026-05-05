"""
策略工作台 **DB 缓存**（回测快照表）子域的对外入口。

- **对外编排 API**（步骤写在同一文件）：``simulator_res_db_cache.write_cache`` / ``read_cache`` / ``apply_cache``
- **步骤内委托**：``orchestration/write``（``ResolveEnv`` 兼容导出）、``orchestration/apply``（paths / serialize）等
- **协调实现**：``DbCacheService``（``service.py``）
- **表读写**：``persistence.snapshot_persist``
- **快照领域**：``domain.snapshot_service.StrategyWorkbenchSnapshotService``
- **枚举 runtime**：``runtime.enumerator_runtime_service``（CLI/BFF）
- **Settings**：``settings.StrategySettingsService``（API ↔ runtime、校验）
- **写次数审计**：``audit.result_summary_audit``
- **指纹**：``finger_print``（``settings_resolver`` / ``env_resolver`` / 编排模块）
- **校验快照（非哈希本身）**：``finger_print.settings_resolver.validated_normalized_snapshot`` — 与 ``settings_fp`` / 表 ``settings_snapshot`` 同源

本包 **根 ``__init__``** 导出 DbCache 列指纹与 ``DbCacheService``；其它见子模块或 ``strategy.services`` 对 snapshot / runtime 的惰性导出。
"""

from __future__ import annotations

from . import config
from .finger_print import (
    db_cache_fingerprint_pair,
    db_cache_fingerprint_pair_from_parts,
    semantic_core,
    settings_fingerprint_id,
    to_env_hash,
    to_settings_hash,
)
from .service import DbCacheService

__all__ = [
    "DbCacheService",
    "config",
    "db_cache_fingerprint_pair",
    "db_cache_fingerprint_pair_from_parts",
    "semantic_core",
    "settings_fingerprint_id",
    "to_env_hash",
    "to_settings_hash",
]
