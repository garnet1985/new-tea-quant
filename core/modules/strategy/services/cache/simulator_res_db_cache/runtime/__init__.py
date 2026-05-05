"""CLI / BFF enumerator wiring（避免顶层 import ``enumerator_runtime_service``，防止与 ``finger_print`` 循环依赖）。"""

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
