"""Portfolio settings (``settings.portfolio``) — 占位壳。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from .settings_base import SettingsBase
from .validation_report import ValidationReport


@dataclass
class PortfolioSettings(SettingsBase):
    """``settings.portfolio``（原 capital_simulator；逻辑未接线，空壳占位）。"""

    raw_settings: Dict[str, Any]

    @property
    def portfolio(self) -> Dict[str, Any]:
        return SettingsBase.ensure_dict_block(self.raw_settings, "portfolio")

    def apply_defaults(self) -> None:
        return

    def validate(self) -> ValidationReport:
        report = SettingsBase.new_validation()
        if "portfolio" in self.raw_settings and not isinstance(
            self.raw_settings.get("portfolio"), dict
        ):
            SettingsBase.add_critical(
                report,
                "portfolio",
                "portfolio must be dict",
                suggested_fix="Set portfolio to {} or omit",
            )
        if self.raw_settings.get("capital_simulator"):
            SettingsBase.add_critical(
                report,
                "capital_simulator",
                "capital_simulator renamed to portfolio",
                suggested_fix='Rename settings key "capital_simulator" → "portfolio"',
            )
        return report

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.portfolio)


__all__ = ["PortfolioSettings"]
