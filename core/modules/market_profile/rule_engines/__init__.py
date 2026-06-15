#!/usr/bin/env python3
"""Rule engine 注册表。"""

from .amplitude_limit import AmplitudeLimitEngine
from .lot_size import LotSizeEngine
from .settlement import SettlementEngine

REGISTRY = [
    AmplitudeLimitEngine,
    LotSizeEngine,
    SettlementEngine,
]

__all__ = ["REGISTRY", "AmplitudeLimitEngine", "LotSizeEngine", "SettlementEngine"]
