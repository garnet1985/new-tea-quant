#!/usr/bin/env python3
"""amplitude_limit rule engine。"""

from __future__ import annotations

from typing import Any, ClassVar, Dict

from ..shared.base import CompiledRuleBase, MarketRuleEngineBase


class AmplitudeLimitEngine(MarketRuleEngineBase):
    rule_key: ClassVar[str] = "amplitude_limit"

    def parse(self, block: Dict[str, Any]) -> CompiledRuleBase:
        pass


__all__ = ["AmplitudeLimitEngine"]
