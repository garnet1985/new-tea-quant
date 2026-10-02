"""枚举层无单笔铺平（sea）。"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

from core.modules.strategy.core.enums import SimulateKind

from ..plan import AttributionCell
from .base import TradesBase


class EnumerateTrades(TradesBase):
    LAYER = "enumerate"
    KIND = SimulateKind.ENUMERATE

    @classmethod
    def run(
        cls,
        folder: Path,
        unique_cells: Sequence[AttributionCell],
        executed: Mapping[str, Any],
    ) -> Dict[str, Any]:
        return {
            "status": "skipped",
            "reason": "trades_not_applicable",
            "layer": cls.LAYER,
            "n": 0,
        }
