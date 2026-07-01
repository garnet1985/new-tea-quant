"""entity_based 模式 runtime status。"""
from __future__ import annotations

from dataclasses import dataclass

from core.modules.strategy.core.engines.enumerator.shared.runtime import RuntimeStatus


@dataclass
class EntityBasedRuntimeStatus(RuntimeStatus):
    """entity_based 模式专用 RuntimeStatus。"""


__all__ = ["EntityBasedRuntimeStatus"]
