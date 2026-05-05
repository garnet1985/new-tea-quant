"""
后端 **枚举运行期胶水**（启动 ``OpportunityEnumeratorFlow``、universe、运行期指纹等）。

**不属于 DbCache**：与「按指纹读写快照表」无关；位于 ``strategy.services.runtime``，与 ``StrategyEnumeratorBootstrapService`` 等并列。
``finger_print`` 通过相对导入引用本包中的 ``run_types`` / ``run_service``（惰性子导出），避免循环依赖。

惰性导出 ``EnumeratorRuntimeService`` / ``EnumeratorRuntimeContext``，避免顶层直接 import ``enumerator_runtime_service`` 触发初始化顺序问题。
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "EnumeratorRuntimeContext",
    "EnumeratorRuntimeService",
]


def __getattr__(name: str) -> Any:
    if name == "EnumeratorRuntimeContext":
        from .enumerator_runtime_service import EnumeratorRuntimeContext

        return EnumeratorRuntimeContext
    if name == "EnumeratorRuntimeService":
        from .enumerator_runtime_service import EnumeratorRuntimeService

        return EnumeratorRuntimeService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(__all__)
