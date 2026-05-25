#!/usr/bin/env python3
"""amplitude_limit Compiled / Resolved dataclasses。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ..shared.base import CompiledRuleBase
from ..shared.matching import match_stock_id
from .helper import compute_limit_prices_from_ratio
from .risk_ratios import parse_risk_ratio_map, resolve_ratio_with_risk


@dataclass(frozen=True)
class AmplitudeLimitEntry:
    entry_key: str
    matching: Dict[str, Any]
    ratio: float
    risk_ratios: Dict[str, float] = field(default_factory=dict)


@dataclass
class AmplitudeLimitCompiled(CompiledRuleBase):
    default_ratio: float
    default_risk_ratios: Dict[str, float] = field(default_factory=dict)
    price_round_decimals: int = 2
    entries: List[AmplitudeLimitEntry] = field(default_factory=list)

    def _matched_entry(self, stock_id: str) -> Optional[AmplitudeLimitEntry]:
        for entry in self.entries:
            if match_stock_id(stock_id, entry.matching):
                return entry
        return None

    def resolve_ratio(
        self,
        stock_id: str,
        status_tags: Optional[Sequence[str]] = None,
    ) -> float:
        entry = self._matched_entry(stock_id)
        if entry is not None:
            base = entry.ratio
            risk_map = entry.risk_ratios
        else:
            base = self.default_ratio
            risk_map = self.default_risk_ratios
        return resolve_ratio_with_risk(base, risk_map, status_tags)

    def resolve(self, stock_id: str, status_tags: Optional[Sequence[str]] = None) -> float:
        return self.resolve_ratio(stock_id, status_tags)

    def compute_limit_prices(
        self,
        stock_id: str,
        prev_close: float,
        status_tags: Optional[Sequence[str]] = None,
    ) -> Tuple[float, float]:
        ratio = self.resolve_ratio(stock_id, status_tags)
        return compute_limit_prices_from_ratio(
            prev_close,
            ratio,
            decimals=self.price_round_decimals,
        )


__all__ = ["AmplitudeLimitCompiled", "AmplitudeLimitEntry"]
