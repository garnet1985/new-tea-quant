#!/usr/bin/env python3
"""策略 data 配置块。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from core.modules.data_contract.contract_const import DataKey
from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
    StrategySettings as StrategySettingsDictModel,
)

from .settings_base import SettingsBase, ValidationReport


@dataclass
class StrategyDataSettings(SettingsBase):
    data: Dict[str, Any]

    @classmethod
    def from_strategy_root(cls, root: Dict[str, Any]) -> "StrategyDataSettings":
        if not isinstance(root, dict):
            root = {}
        block = root.get("data")
        if not isinstance(block, dict):
            block = {}
            root["data"] = block
        return cls(data=block)

    def apply_defaults(self) -> None:
        d = self.data
        if "min_required_records" not in d or not isinstance(
            d.get("min_required_records"), int
        ) or d.get("min_required_records", 0) <= 0:
            d["min_required_records"] = 100
        if "indicators" not in d:
            d["indicators"] = {}
        if "extra_required_data_sources" not in d or not isinstance(
            d.get("extra_required_data_sources"), list
        ):
            d["extra_required_data_sources"] = []
        base = d.get("base_required_data")
        if isinstance(base, dict) and base.get("params") is None:
            base["params"] = {}

    def validate(self) -> ValidationReport:
        result = SettingsBase.new_validation()
        self.apply_defaults()
        try:
            StrategySettingsDictModel.validate_data_config(self.data)
        except ValueError as e:
            SettingsBase.add_critical(
                result,
                "data",
                str(e),
            )
        return result

    def to_dict(self) -> Dict[str, Any]:
        return self.deep_copy_dict(self.data)

    @property
    def base_required_data(self) -> Dict[str, Any]:
        base = self.data.get("base_required_data")
        return base if isinstance(base, dict) else {}

    @property
    def extra_required_data_sources(self) -> List[Dict[str, Any]]:
        xs = self.data.get("extra_required_data_sources", [])
        if xs is None or not isinstance(xs, list):
            return []
        return list(xs)

    @property
    def min_required_records(self) -> int:
        min_records = self.data.get("min_required_records", 100)
        try:
            return max(int(min_records), 1)
        except (TypeError, ValueError):
            return 100

    @property
    def indicators_config(self) -> Dict[str, Any]:
        return self.data.get("indicators", {}) or {}

    @property
    def base_data_id(self) -> str:
        base = self.base_required_data
        if not base:
            return DataKey.STOCK_KLINE.value
        try:
            return StrategySettingsDictModel.normalize_base_required_data(base)["data_id"]
        except ValueError:
            return str(base.get("data_id", "") or "")

    @property
    def adjust_type(self) -> str:
        view = StrategySettingsDictModel({"data": self.data})
        return view.adjust_type


__all__ = ["StrategyDataSettings"]
