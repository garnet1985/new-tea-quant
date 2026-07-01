#!/usr/bin/env python3
"""根级 fees：全链路模拟唯一费率来源（见 settings_example schema v2）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from .settings_base import SettingsBase, ValidationReport


@dataclass
class StrategyFeesSettings(SettingsBase):
    """附着在 StrategySettings.raw_settings 上，校验根级 `fees`。"""

    raw_settings: Dict[str, Any]

    @classmethod
    def from_strategy_root(cls, root: dict) -> "StrategyFeesSettings":
        if not isinstance(root, dict):
            root = {}
        if "fees" not in root or not isinstance(root.get("fees"), dict):
            root["fees"] = {}
        return cls(raw_settings=root)

    def apply_defaults(self) -> None:
        f = self.raw_settings.get("fees")
        if not isinstance(f, dict):
            f = {}
            self.raw_settings["fees"] = f
        f.setdefault("commission_rate", 0.00025)
        f.setdefault("min_commission", 5.0)
        f.setdefault("stamp_duty_rate", 0.001)
        f.setdefault("transfer_fee_rate", 0.0)

    def validate(self) -> ValidationReport:
        result = SettingsBase.new_validation()
        self.apply_defaults()
        f = self.raw_settings.get("fees") or {}
        if not isinstance(f, dict):
            SettingsBase.add_critical(result, "fees", "fees 必须为对象（dict）")
            return result

        pairs = (
            ("commission_rate", "commission_rate 须为数字"),
            ("min_commission", "min_commission 须为数字"),
            ("stamp_duty_rate", "stamp_duty_rate 须为数字"),
            ("transfer_fee_rate", "transfer_fee_rate 须为数字"),
        )
        for key, msg in pairs:
            if key not in f:
                continue
            try:
                float(f[key])
            except (TypeError, ValueError):
                SettingsBase.add_critical(result, f"fees.{key}", msg)

        return result

    def to_dict(self) -> Dict[str, Any]:
        self.apply_defaults()
        return self.deep_copy_dict(dict(self.raw_settings.get("fees") or {}))


__all__ = ["StrategyFeesSettings"]
