"""``settings.analysis`` — 回测后是否自动收集归因 input。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from .settings_base import SettingsBase
from .validation_report import ValidationReport


@dataclass
class AnalysisSettings(SettingsBase):
    """``settings.analysis`` — 归因开关（不进指纹）。"""

    raw_settings: Dict[str, Any]

    def _block(self) -> Dict[str, Any]:
        block = self.raw_settings.get("analysis")
        if not isinstance(block, dict):
            block = {}
            self.raw_settings["analysis"] = block
        return block

    @property
    def enabled(self) -> bool:
        value = self._block().get("enabled", False)
        return bool(value) if isinstance(value, bool) else False

    def apply_defaults(self) -> None:
        block = self._block()
        if "enabled" not in block:
            block["enabled"] = False
        elif not isinstance(block.get("enabled"), bool):
            block["enabled"] = False

    def validate(self) -> ValidationReport:
        report = SettingsBase.new_validation()
        if "analysis" in self.raw_settings and not isinstance(
            self.raw_settings.get("analysis"), dict
        ):
            SettingsBase.add_critical(
                report,
                "analysis",
                "analysis must be dict",
                suggested_fix='Set analysis to {"enabled": false} or omit',
            )
            return report
        self.apply_defaults()
        enabled = self._block().get("enabled", False)
        if not isinstance(enabled, bool):
            SettingsBase.add_warning(
                report,
                "analysis.enabled",
                "analysis.enabled should be bool",
                suggested_fix="Set analysis.enabled to true or false",
            )
        return report

    def to_dict(self) -> Dict[str, Any]:
        self.apply_defaults()
        return SettingsBase.deep_copy_dict(dict(self._block()))


__all__ = ["AnalysisSettings"]
