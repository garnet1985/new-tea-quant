#!/usr/bin/env python3
"""lot_size rule engine。"""

from __future__ import annotations

from typing import Any, ClassVar, Dict

from ..shared.base import CompiledRuleBase, MarketRuleEngineBase


class LotSizeEngine(MarketRuleEngineBase):
    rule_key: ClassVar[str] = "lot_size"

    def parse(self, block: Dict[str, Any]) -> CompiledRuleBase:
        pass


__all__ = ["LotSizeEngine"]
