"""Scanner settings (``settings.scanner``) — 占位壳。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from .settings_base import SettingsBase
from .validation_report import ValidationReport


@dataclass
class ScannerSettings(SettingsBase):
    """``settings.scanner`` 空壳（与 SOT section 一一对应；逻辑未接线）。"""

    raw_settings: Dict[str, Any]

    @property
    def scanner(self) -> Dict[str, Any]:
        return SettingsBase.ensure_dict_block(self.raw_settings, "scanner")

    def apply_defaults(self) -> None:
        return

    def validate(self) -> ValidationReport:
        report = SettingsBase.new_validation()
        if "scanner" in self.raw_settings and not isinstance(
            self.raw_settings.get("scanner"), dict
        ):
            SettingsBase.add_critical(
                report,
                "scanner",
                "scanner must be dict",
                suggested_fix="Set scanner to {} or omit",
            )
        return report

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.scanner)


__all__ = ["ScannerSettings"]
