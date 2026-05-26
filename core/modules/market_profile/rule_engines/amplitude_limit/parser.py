#!/usr/bin/env python3
"""amplitude_limit rule engine。"""

from __future__ import annotations

from typing import Any, ClassVar, Dict, List

from ..shared.base import CompiledRuleBase, MarketRuleEngineBase
from ..shared.rule_entry import max_matching_prefix_len
from .models import AmplitudeLimitCompiled, AmplitudeLimitEntry
from .risk_ratios import parse_risk_ratio_map


class AmplitudeLimitEngine(MarketRuleEngineBase):
    rule_key: ClassVar[str] = "amplitude_limit"

    def parse(self, block: Dict[str, Any]) -> CompiledRuleBase:
        try:
            default_ratio = float(block.get("default_ratio", 0.1))
        except (TypeError, ValueError):
            default_ratio = 0.1
        try:
            decimals = int(block.get("price_round_decimals", 2))
        except (TypeError, ValueError):
            decimals = 2

        default_risk_ratios = parse_risk_ratio_map(block.get("default_risk"))

        entries: List[AmplitudeLimitEntry] = []
        for item in block.get("rules") or []:
            if not isinstance(item, dict):
                continue
            matching = item.get("matching")
            if not isinstance(matching, dict):
                continue
            try:
                ratio = float(item.get("ratio", default_ratio))
            except (TypeError, ValueError):
                ratio = default_ratio
            entries.append(
                AmplitudeLimitEntry(
                    entry_key=str(item.get("key") or "").strip(),
                    matching=matching,
                    ratio=ratio,
                    risk_ratios=parse_risk_ratio_map(item.get("risk")),
                )
            )

        entries.sort(key=lambda e: max_matching_prefix_len(e.matching), reverse=True)
        return AmplitudeLimitCompiled(
            default_ratio=default_ratio,
            default_risk_ratios=default_risk_ratios,
            price_round_decimals=max(decimals, 0),
            entries=entries,
        )


__all__ = ["AmplitudeLimitEngine"]
