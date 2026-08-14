"""``settings.tag_definitions`` — 标签定义列表。

消费者: TagSettings
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict, List

from .settings_base import SettingsBase
from .validation_report import ValidationReport


@dataclass
class TagDefinitionItem:
    """单条 tag 定义。"""

    name: str
    display_name: str = ""
    description: str = ""

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "TagDefinitionItem":
        if not isinstance(raw, dict):
            raise ValueError("tag_definitions 条目须为 dict")
        name = str(raw.get("name") or "").strip()
        if not name:
            raise ValueError("tag_definitions[].name 必填")
        display = str(raw.get("display_name") or name).strip()
        description = str(raw.get("description") or "").strip()
        return cls(name=name, display_name=display, description=description)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "display_name": self.display_name or self.name,
            "description": self.description,
        }


@dataclass
class TagDefinitionSettings(SettingsBase):
    """``settings.tag_definitions``。"""

    raw_settings: Dict[str, Any]

    @property
    def raw_list(self) -> List[Any]:
        block = self.raw_settings.get("tag_definitions")
        return list(block) if isinstance(block, list) else []

    def items(self) -> List[TagDefinitionItem]:
        return [TagDefinitionItem.from_dict(x) for x in self.raw_list]

    def apply_defaults(self) -> None:
        if "tag_definitions" not in self.raw_settings or not isinstance(
            self.raw_settings.get("tag_definitions"), list
        ):
            self.raw_settings["tag_definitions"] = []

    def validate(self) -> ValidationReport:
        report = SettingsBase.new_validation()
        raw = self.raw_settings.get("tag_definitions")
        if raw is None:
            SettingsBase.add_critical(
                report,
                "tag_definitions",
                "tag_definitions is required",
                suggested_fix='Set tag_definitions to [{"name": "..."}]',
            )
            return report
        if not isinstance(raw, list):
            SettingsBase.add_critical(
                report,
                "tag_definitions",
                "tag_definitions must be list",
            )
            return report
        if len(raw) == 0:
            SettingsBase.add_critical(
                report,
                "tag_definitions",
                "tag_definitions must contain at least one item",
            )
            return report

        seen = set()
        for i, item in enumerate(raw):
            try:
                parsed = TagDefinitionItem.from_dict(item)
            except ValueError as exc:
                SettingsBase.add_critical(
                    report, f"tag_definitions[{i}]", str(exc)
                )
                continue
            if parsed.name in seen:
                SettingsBase.add_critical(
                    report,
                    f"tag_definitions[{i}].name",
                    f"duplicate tag name {parsed.name!r}",
                )
            seen.add(parsed.name)

        return report

    def to_dict(self) -> List[Dict[str, Any]]:
        self.apply_defaults()
        out: List[Dict[str, Any]] = []
        for raw in self.raw_list:
            try:
                out.append(TagDefinitionItem.from_dict(raw).to_dict())
            except ValueError:
                if isinstance(raw, dict):
                    out.append(deepcopy(raw))
        return out


__all__ = ["TagDefinitionItem", "TagDefinitionSettings"]
