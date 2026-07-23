"""Meta settings (``settings.meta``)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from .settings_base import SettingsBase
from .validation_report import ValidationReport


@dataclass
class MetaSettings(SettingsBase):
    """``settings.meta``（展示 / CLI alias；不含 core / is_enabled）。"""

    raw_settings: Dict[str, Any]

    @property
    def meta(self) -> Dict[str, Any]:
        return SettingsBase.ensure_dict_block(self.raw_settings, "meta")

    @property
    def key(self) -> str:
        return str(self.meta.get("key") or "").strip()

    @property
    def display_name(self) -> str:
        return str(self.meta.get("display_name") or "").strip()

    @property
    def description(self) -> str:
        desc = self.meta.get("description")
        if desc is None:
            return ""
        if isinstance(desc, str):
            return desc.strip()
        if isinstance(desc, list):
            parts = [str(item).strip() for item in desc if item and str(item).strip()]
            return "".join(parts)
        return str(desc).strip()

    def apply_defaults(self) -> None:
        if "meta" not in self.raw_settings or not isinstance(self.raw_settings["meta"], dict):
            self.raw_settings["meta"] = {}
        if "display_name" not in self.meta:
            self.raw_settings["meta"]["display_name"] = ""

    def validate(self) -> ValidationReport:
        report = SettingsBase.new_validation()
        self.apply_defaults()
        if not isinstance(self.raw_settings.get("meta"), dict):
            SettingsBase.add_critical(
                report,
                "meta",
                "meta must be dict",
                suggested_fix='Set meta to {"key": "...", "display_name": "..."}',
            )
        return report

    def to_dict(self) -> Dict[str, Any]:
        self.apply_defaults()
        return dict(self.meta)


__all__ = ["MetaSettings"]
