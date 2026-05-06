#!/usr/bin/env python3
"""
策略 DB 缓存 **指纹** 包。

**职责划分**

- ``settings_resolver`` / ``env_resolver``：**收集与组装**（规范化快照、语义核 dict、env 因子 / env 载荷 dict）。
- ``finger_print``（模块 ``finger_print.py``）：**对外哈希 API**（``to_settings_hash`` / ``to_env_hash``）与 DbCache 编排。

顶层 **惰性导出**，减轻初始化阶段导入负担。

运行期请求指纹与枚举 universe 解析在 ``strategy.services.runtime``（非 DbCache 子包）。
"""

from __future__ import annotations

from typing import Any

from ....runtime.run_types import StrategyRunFingerprint

_RUNTIME_SERVICE = frozenset({"StrategyFingerprintManager", "StrategyFingerprintRuntimeService"})
_SETTINGS_RESOLVER = frozenset(
    {
        "validated_normalized_snapshot",
        "semantic_core",
        "semantic_core_from_strategy_settings",
        "strip_to_semantic_core",
        "resolve_sampling_is_used",
    }
)
_ENV_RESOLVER = frozenset(
    {"EnvFingerprintInputs", "ResolveEnv", "resolve_env_inputs", "env_fingerprint_payload"}
)
_FP_API = frozenset(
    {
        "DbCacheFingerprintResolution",
        "resolve_db_cache_fingerprints",
        "db_cache_fingerprint_pair",
        "db_cache_fingerprint_pair_from_parts",
        "settings_fingerprint_id",
        "to_env_hash",
        "to_settings_hash",
    }
)

__all__ = [
    "DbCacheFingerprintResolution",
    "EnvFingerprintInputs",
    "ResolveEnv",
    "StrategyFingerprintManager",
    "StrategyFingerprintRuntimeService",
    "StrategyRunFingerprint",
    "db_cache_fingerprint_pair",
    "db_cache_fingerprint_pair_from_parts",
    "env_fingerprint_payload",
    "resolve_db_cache_fingerprints",
    "resolve_env_inputs",
    "resolve_sampling_is_used",
    "semantic_core",
    "semantic_core_from_strategy_settings",
    "settings_fingerprint_id",
    "strip_to_semantic_core",
    "to_env_hash",
    "to_settings_hash",
    "validated_normalized_snapshot",
]


def __getattr__(name: str) -> Any:
    if name in _RUNTIME_SERVICE:
        from ....runtime import run_service

        return getattr(run_service, name)
    if name in _SETTINGS_RESOLVER:
        from . import settings_resolver

        return getattr(settings_resolver, name)
    if name in _ENV_RESOLVER:
        from . import env_resolver

        return getattr(env_resolver, name)
    if name in _FP_API:
        from . import finger_print as fp_orch

        return getattr(fp_orch, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(__all__)
