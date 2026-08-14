"""``settings.data`` — base/required 数据声明校验。

本文件:
- DataSettings: base_data_key、required 声明结构与校验
  边界: 负责 data section 校验；不负责 Contract 加载（StrategyDataResolver / loaders）
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict, List

from .settings_base import SettingsBase
from .validation_report import ValidationReport


@dataclass
class DataSettings(SettingsBase):
    """``settings.data`` — base K 线 + required 附加数据源。"""

    raw_settings: Dict[str, Any]

    @property
    def data(self) -> Dict[str, Any]:
        return SettingsBase.ensure_dict_block(self.raw_settings, "data")

    @property
    def base(self) -> Dict[str, Any]:
        block = self.data.get("base")
        return dict(block) if isinstance(block, dict) else {}

    @property
    def base_data_key(self) -> str:
        return self.normalize_base(self.base)["data_key"]

    @property
    def min_required_records(self) -> int:
        try:
            return max(int(self.data.get("min_required_records") or 0), 0)
        except (TypeError, ValueError):
            return 0

    def apply_defaults(self) -> None:
        if "data" not in self.raw_settings or not isinstance(self.raw_settings["data"], dict):
            self.raw_settings["data"] = {}
        data = self.raw_settings["data"]
        if "base" not in data or not isinstance(data.get("base"), dict):
            data["base"] = {
                "data_key": "stock.kline.daily",
                "params": {"adjust": "qfq"},
                "indicators": {},
            }
        base = data["base"]
        if not str(base.get("data_key") or "").strip():
            base["data_key"] = "stock.kline.daily"
        if "params" not in base or not isinstance(base.get("params"), dict):
            base["params"] = {"adjust": "qfq"}
        if "indicators" not in base or not isinstance(base.get("indicators"), dict):
            base["indicators"] = {}
        if "required" not in data or not isinstance(data.get("required"), list):
            data["required"] = []
        if "min_required_records" not in data:
            data["min_required_records"] = 100

    def validate(self) -> ValidationReport:
        report = SettingsBase.new_validation()
        self.apply_defaults()

        if not isinstance(self.raw_settings.get("data"), dict):
            SettingsBase.add_critical(
                report,
                "data",
                "data must be dict",
                suggested_fix="Set data to {}",
            )
            return report

        try:
            self.normalize_base(self.base)
        except ValueError as exc:
            SettingsBase.add_critical(report, "data.base", str(exc))

        required = self.data.get("required")
        if required is not None and not isinstance(required, list):
            SettingsBase.add_critical(
                report,
                "data.required",
                "data.required must be list",
            )

        if report.is_valid:
            try:
                self.issue_declarations()
            except ValueError as exc:
                SettingsBase.add_critical(report, "data", str(exc))

        return report

    @classmethod
    def normalize_indicators(cls, raw: Any) -> Dict[str, Any]:
        if raw is None:
            return {}
        if not isinstance(raw, dict):
            raise ValueError("indicators 须为 dict")
        return deepcopy(raw)

    def normalize_base(self, block: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(block, dict):
            raise ValueError("data.base 须为 dict")
        data_key = str(block.get("data_key") or "").strip()
        if not data_key:
            raise ValueError("data.base 缺少 data_key")
        return {
            "data_key": data_key,
            "params": dict(block.get("params") or {}),
            "indicators": self.normalize_indicators(block.get("indicators")),
        }

    def normalize_declaration_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(item, dict):
            raise ValueError("data.required 条目须为 dict")
        data_key = str(item.get("data_key") or "").strip()
        if not data_key:
            raise ValueError("data.required 条目缺少 data_key")
        return {
            "data_key": data_key,
            "params": dict(item.get("params") or {}),
            "indicators": self.normalize_indicators(item.get("indicators")),
        }

    @staticmethod
    def storage_key_for(data_key: Any, *, is_base: bool) -> str:
        key = str(data_key)
        return "base" if is_base else key

    def issue_declarations(self) -> List[Dict[str, Any]]:
        decls: List[Dict[str, Any]] = [self.normalize_base(self.base)]
        seen = {decls[0]["data_key"]}
        for raw in self.data.get("required") or []:
            item = self.normalize_declaration_item(raw)
            data_key = item["data_key"]
            if data_key in seen:
                raise ValueError(f"duplicate data_key: {data_key}")
            seen.add(data_key)
            decls.append(item)
        return decls

    def to_dict(self) -> Dict[str, Any]:
        self.apply_defaults()
        return deepcopy(self.data)


__all__ = ["DataSettings"]
