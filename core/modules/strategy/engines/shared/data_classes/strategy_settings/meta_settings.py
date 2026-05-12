#!/usr/bin/env python3
"""策略 Meta 设置。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from .settings_base import SettingsBase, ValidationReport


@dataclass
class StrategyMetaSettings(SettingsBase):
    name: str
    description: str
    core: Dict[str, Any]
    is_enabled: bool = False

    @classmethod
    def from_raw(cls, raw: Dict[str, Any]) -> "StrategyMetaSettings":
        if not isinstance(raw, dict):
            raw = {}
        name = raw.get("name", "unknown")
        if name is not None and not isinstance(name, str):
            name = str(name)
        desc = raw.get("description", "")
        if desc is not None and not isinstance(desc, str):
            desc = str(desc)
        core = raw.get("core", {})
        if core is None or not isinstance(core, dict):
            core = {}
        inst = cls(
            name=name or "unknown",
            description=desc or "",
            core=dict(core),
            is_enabled=bool(raw.get("is_enabled", False)),
        )
        inst.apply_defaults()
        return inst

    def apply_defaults(self) -> None:
        self.name = str(self.name) if self.name is not None else "unknown"
        self.description = str(self.description) if self.description is not None else ""
        self.is_enabled = bool(self.is_enabled)
        self.core = dict(self.core) if isinstance(self.core, dict) else {}

    def validate(self) -> ValidationReport:
        self.apply_defaults()
        result = SettingsBase.new_validation()
        if not self.name or self.name.strip() == "" or self.name == "unknown":
            SettingsBase.add_critical(
                result,
                "name",
                "策略名称不能为空或为 'unknown'",
                suggested_fix='在 settings.py 中设置 "name": "your_strategy_name"',
            )
        if not isinstance(self.core, dict):
            SettingsBase.add_critical(
                result,
                "core",
                "core 必须为对象（dict）",
                suggested_fix='将 "core" 设为 {} 或包含策略参数的对象',
            )
        if not (self.description or "").strip():
            SettingsBase.add_warning(
                result,
                "description",
                "未填写 description，建议补充策略说明",
            )
        return result

    def to_dict(self) -> Dict[str, Any]:
        return self.deep_copy_dict(
            {
                "name": self.name,
                "description": self.description,
                "core": self.core,
                "is_enabled": self.is_enabled,
            }
        )

    @property
    def strategy_name(self) -> str:
        return self.name


__all__ = ["StrategyMetaSettings"]
