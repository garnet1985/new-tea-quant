#!/usr/bin/env python3
"""Rule engine 与 Compiled 规则基类。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar, Dict


class CompiledRuleBase(ABC):
    @abstractmethod
    def resolve(self, stock_id: str) -> Any:
        pass


class MarketRuleEngineBase(ABC):
    rule_key: ClassVar[str]

    @abstractmethod
    def parse(self, block: Dict[str, Any]) -> CompiledRuleBase:
        pass


__all__ = ["CompiledRuleBase", "MarketRuleEngineBase"]
