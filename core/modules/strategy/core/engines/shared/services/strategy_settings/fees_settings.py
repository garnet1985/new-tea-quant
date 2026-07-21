"""Fees settings (``settings.fees``) — 占位壳，字段校验后续补。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from .settings_base import SettingsBase
from .validation_report import ValidationReport


@dataclass
class FeesSettings(SettingsBase):
    """``settings.fees`` 空壳（与 SOT section 一一对应；逻辑未接线）。"""

    raw_settings: Dict[str, Any]

    @property
    def fees(self) -> Dict[str, Any]:
        return SettingsBase.ensure_dict_block(self.raw_settings, "fees")

    def apply_defaults(self) -> None:
        return

    def validate(self) -> ValidationReport:
        report = SettingsBase.new_validation()
        if "fees" in self.raw_settings and not isinstance(
            self.raw_settings.get("fees"), dict
        ):
            SettingsBase.add_critical(
                report,
                "fees",
                "fees must be dict",
                suggested_fix="Set fees to {} or omit",
            )
        return report

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.fees)


__all__ = ["FeesSettings"]
