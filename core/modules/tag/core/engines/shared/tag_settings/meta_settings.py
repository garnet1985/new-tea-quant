"""Meta settings (``settings.meta``).

消费者: TagSettings
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from .settings_base import SettingsBase
from .validation_report import ValidationReport


@dataclass
class MetaSettings(SettingsBase):
    """``settings.meta``（展示 / CLI alias）。"""

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

    @property
    def keywords(self) -> List[str]:
        raw = self.meta.get("keywords")
        if not isinstance(raw, list):
            return []
        return [str(x).strip() for x in raw if str(x).strip()]

    @property
    def details(self) -> Dict[str, Any]:
        block = self.meta.get("details")
        return dict(block) if isinstance(block, dict) else {}

    @property
    def category(self) -> List[str]:
        raw = self.meta.get("category")
        if not isinstance(raw, list):
            return []
        return [str(x).strip() for x in raw if str(x).strip()]

    def apply_defaults(self) -> None:
        if "meta" not in self.raw_settings or not isinstance(self.raw_settings["meta"], dict):
            self.raw_settings["meta"] = {}
        meta = self.raw_settings["meta"]
        meta.setdefault("display_name", "")
        meta.setdefault("description", "")
        meta.setdefault("keywords", [])
        meta.setdefault("details", {})
        meta.setdefault("category", [])

    def ensure_key(self, fallback: str) -> str:
        """若 meta.key 为空，写入 fallback（通常为目录 tag_key）。"""
        self.apply_defaults()
        key = self.key
        if key:
            return key
        key = str(fallback or "").strip()
        if not key:
            raise ValueError("meta.key 不能为空")
        self.raw_settings["meta"]["key"] = key
        return key

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
        if not self.key:
            SettingsBase.add_critical(
                report,
                "meta.key",
                "meta.key is required",
                suggested_fix='Set meta.key to a globally unique alias',
            )
        if not self.display_name:
            SettingsBase.add_warning(
                report,
                "meta.display_name",
                "meta.display_name is empty",
                suggested_fix="Set a human-readable display_name",
            )
        return report

    def to_dict(self) -> Dict[str, Any]:
        self.apply_defaults()
        return dict(self.meta)


__all__ = ["MetaSettings"]
