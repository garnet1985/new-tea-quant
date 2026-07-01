"""entity_based 运行状态 context。"""
from __future__ import annotations

from core.modules.strategy.core.engines.enumerator.shared.runtime import RuntimeStatus


class EntityRuntimeStatus(RuntimeStatus):
    """entity_based 模式运行状态（当前与共享 RuntimeStatus 一致）。"""


__all__ = ["EntityRuntimeStatus"]
