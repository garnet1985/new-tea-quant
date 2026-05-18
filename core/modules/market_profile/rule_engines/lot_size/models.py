#!/usr/bin/env python3
"""lot_size Compiled / Resolved dataclasses。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from ..shared.base import CompiledRuleBase
from ..shared.matching import match_stock_id
from .helper import floor_buy_quantity


@dataclass(frozen=True)
class LotSizeEntry:
    entry_key: str
    matching: Dict[str, Any]
    min_lot: int
    lot_step: int


@dataclass(frozen=True)
class LotSizeResolved:
    min_lot: int
    lot_step: int
    board_entry_key: str = "default"


@dataclass
class LotSizeCompiled(CompiledRuleBase):
    default_min_lot: int = 100
    default_lot_step: int = 100
    entries: List[LotSizeEntry] = field(default_factory=list)

    def resolve(self, stock_id: str) -> LotSizeResolved:
        for entry in self.entries:
            if match_stock_id(stock_id, entry.matching):
                return LotSizeResolved(
                    min_lot=entry.min_lot,
                    lot_step=entry.lot_step,
                    board_entry_key=entry.entry_key,
                )
        return LotSizeResolved(
            min_lot=self.default_min_lot,
            lot_step=self.default_lot_step,
            board_entry_key="default",
        )

    def floor_buy_quantity(self, shares: int, stock_id: str) -> int:
        resolved = self.resolve(stock_id)
        return floor_buy_quantity(
            shares,
            min_lot=resolved.min_lot,
            lot_step=resolved.lot_step,
        )


__all__ = ["LotSizeCompiled", "LotSizeEntry", "LotSizeResolved"]
