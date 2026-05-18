#!/usr/bin/env python3
"""amplitude_limit Compiled / Resolved dataclasses。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from ..shared.base import CompiledRuleBase
from ..shared.matching import match_stock_id
from .helper import compute_limit_prices_from_ratio


@dataclass(frozen=True)
class AmplitudeLimitEntry:
    entry_key: str
    matching: Dict[str, Any]
    ratio: float


@dataclass
class AmplitudeLimitCompiled(CompiledRuleBase):
    default_ratio: float
    price_round_decimals: int = 2
    entries: List[AmplitudeLimitEntry] = field(default_factory=list)

    def resolve_ratio(self, stock_id: str) -> float:
        for entry in self.entries:
            if match_stock_id(stock_id, entry.matching):
                return entry.ratio
        return self.default_ratio

    def resolve(self, stock_id: str) -> float:
        return self.resolve_ratio(stock_id)

    def compute_limit_prices(
        self,
        stock_id: str,
        prev_close: float,
    ) -> Tuple[float, float]:
        ratio = self.resolve_ratio(stock_id)
        return compute_limit_prices_from_ratio(
            prev_close,
            ratio,
            decimals=self.price_round_decimals,
        )


__all__ = ["AmplitudeLimitCompiled", "AmplitudeLimitEntry"]
