"""``settings.simulation.price`` — 价格回放去噪。

本文件:
- PriceReplaySettings: opportunity_merge_gap
  边界: 负责价格层合并间隔；不负责成交回放或钩子
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from core.modules.strategy.core.engines.shared.services.strategy_settings.settings_base import (
    SettingsBase,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.validation_report import (
    ValidationReport,
)

DEFAULT_OPPORTUNITY_MERGE_GAP = 1


@dataclass
class PriceReplaySettings(SettingsBase):
    """``settings.simulation.price``。"""

    raw_settings: Dict[str, Any]

    @property
    def simulation(self) -> Dict[str, Any]:
        return SettingsBase.ensure_dict_block(self.raw_settings, "simulation")

    @property
    def price(self) -> Dict[str, Any]:
        block = self.simulation.get("price")
        return block if isinstance(block, dict) else {}

    @property
    def opportunity_merge_gap(self) -> int:
        raw = self.price.get("opportunity_merge_gap")
        if raw is None or isinstance(raw, bool):
            return DEFAULT_OPPORTUNITY_MERGE_GAP
        try:
            return int(raw)
        except (TypeError, ValueError):
            return DEFAULT_OPPORTUNITY_MERGE_GAP

    def apply_defaults(self) -> None:
        sim = self.raw_settings.setdefault("simulation", {})
        if not isinstance(sim, dict):
            self.raw_settings["simulation"] = {}
            sim = self.raw_settings["simulation"]
        block = sim.setdefault("price", {})
        if not isinstance(block, dict):
            sim["price"] = {}
            block = sim["price"]
        block.setdefault("opportunity_merge_gap", DEFAULT_OPPORTUNITY_MERGE_GAP)

    def validate(self) -> ValidationReport:
        report = SettingsBase.new_validation()
        sim = self.raw_settings.get("simulation")
        if sim is None:
            return report
        if not isinstance(sim, dict):
            return report
        raw_block = sim.get("price")
        if raw_block is None:
            return report
        if not isinstance(raw_block, dict):
            SettingsBase.add_critical(
                report,
                "simulation.price",
                "simulation.price must be dict",
                suggested_fix="Set simulation.price to {opportunity_merge_gap: 1}",
            )
            return report
        raw = raw_block.get("opportunity_merge_gap")
        if raw is None:
            return report
        if isinstance(raw, bool) or not isinstance(raw, int):
            SettingsBase.add_critical(
                report,
                "simulation.price.opportunity_merge_gap",
                "opportunity_merge_gap must be an integer >= 0",
                suggested_fix="Use 0 (never merge by gap) or 1 (adjacent bars)",
            )
            return report
        if int(raw) < 0:
            SettingsBase.add_critical(
                report,
                "simulation.price.opportunity_merge_gap",
                "opportunity_merge_gap must be >= 0",
                suggested_fix="Use 0 or a positive integer",
            )
        return report

    def to_dict(self) -> Dict[str, Any]:
        self.apply_defaults()
        return {"opportunity_merge_gap": int(self.opportunity_merge_gap)}


__all__ = ["DEFAULT_OPPORTUNITY_MERGE_GAP", "PriceReplaySettings"]
