#!/usr/bin/env python3
"""lot_size rule engine。"""

from __future__ import annotations

from typing import Any, ClassVar, Dict, List

from ..shared.base import CompiledRuleBase, MarketRuleEngineBase
from ..shared.rule_entry import max_matching_prefix_len
from .models import LotSizeCompiled, LotSizeEntry


class LotSizeEngine(MarketRuleEngineBase):
    rule_key: ClassVar[str] = "lot_size"

    def parse(self, block: Dict[str, Any]) -> CompiledRuleBase:
        try:
            default_min = max(int(block.get("default_min_lot", 100)), 1)
        except (TypeError, ValueError):
            default_min = 100
        try:
            default_step = max(int(block.get("default_lot_step", 100)), 1)
        except (TypeError, ValueError):
            default_step = 100

        entries: List[LotSizeEntry] = []
        for item in block.get("rules") or []:
            if not isinstance(item, dict):
                continue
            matching = item.get("matching")
            if not isinstance(matching, dict):
                continue
            try:
                min_lot = max(int(item.get("min_lot", default_min)), 1)
            except (TypeError, ValueError):
                min_lot = default_min
            try:
                lot_step = max(int(item.get("lot_step", default_step)), 1)
            except (TypeError, ValueError):
                lot_step = default_step
            entries.append(
                LotSizeEntry(
                    entry_key=str(item.get("key") or "").strip(),
                    matching=matching,
                    min_lot=min_lot,
                    lot_step=lot_step,
                )
            )

        entries.sort(key=lambda e: max_matching_prefix_len(e.matching), reverse=True)
        return LotSizeCompiled(
            default_min_lot=default_min,
            default_lot_step=default_step,
            entries=entries,
        )


__all__ = ["LotSizeEngine"]
