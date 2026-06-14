#!/usr/bin/env python3
"""settlement rule engine。"""

from __future__ import annotations

from typing import Any, ClassVar, Dict

from ..shared.base import CompiledRuleBase, MarketRuleEngineBase
from .models import SettlementCompiled


class SettlementEngine(MarketRuleEngineBase):
    rule_key: ClassVar[str] = "settlement"

    def parse(self, block: Dict[str, Any]) -> CompiledRuleBase:
        raw = block.get("t_plus", 0)
        try:
            t_plus = max(int(raw), 0)
        except (TypeError, ValueError):
            t_plus = 0
        return SettlementCompiled(t_plus=t_plus)


__all__ = ["SettlementEngine"]
