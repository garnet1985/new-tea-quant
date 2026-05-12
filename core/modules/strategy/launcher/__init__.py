"""
策略 **launcher**：与 ``execution_manager`` 同级；运行期启动与工作台数据面（枚举 runtime、
settings/指纹、工作台快照与目录 API、扫描异步入口等）。

与 ``services.cache.simulator_res_db_cache``（DbCache）分列：本包不做「按指纹命中缓存」编排。

惰性子导出减轻 import 成本；``fetch_latest_workbench_snapshot`` 见 ``workbench`` 模块。
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "EnumeratorRuntimeContext",
    "EnumeratorRuntimeService",
    "StrategySettingsService",
    "fetch_latest_workbench_snapshot",
]


def __getattr__(name: str) -> Any:
    if name == "EnumeratorRuntimeContext":
        from .enumerator_runtime_service import EnumeratorRuntimeContext

        return EnumeratorRuntimeContext
    if name == "EnumeratorRuntimeService":
        from .enumerator_runtime_service import EnumeratorRuntimeService

        return EnumeratorRuntimeService
    if name == "StrategySettingsService":
        from .run_service import StrategySettingsService

        return StrategySettingsService
    if name == "fetch_latest_workbench_snapshot":
        from .workbench import fetch_latest_workbench_snapshot

        return fetch_latest_workbench_snapshot
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(__all__)
