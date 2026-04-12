#!/usr/bin/env python3
"""
策略 ``data`` 配置块（对应 ``settings_example`` 第 3) 节）。

职责：
- 持有顶层 ``settings["data"]`` 的 **同一 dict 引用**（便于与整包 settings 同步）
- ``apply_defaults``：data 域内默认值与最小结构
- ``validate``：契约校验（委托 ``StrategySettings`` 字典模型的 ``validate_data_config``）
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from core.modules.data_contract.contract_const import DataKey
from core.modules.strategy.models.strategy_settings import StrategySettings as StrategySettingsDictModel

from .settings_base import SettingsBase, ValidationReport


@dataclass
class StrategyDataSettings(SettingsBase):
    """
    ``data`` 根下的配置：base_required_data、extra_required_data_sources、
    min_required_records、indicators 等。
    """

    data: Dict[str, Any]

    @classmethod
    def from_strategy_root(cls, root: Dict[str, Any]) -> StrategyDataSettings:
        """
        从完整策略 ``settings`` 字典挂载 ``data`` 子树。

        若缺少或非 dict，则在 ``root`` 上写入 ``{}`` 并沿用该引用。
        """
        if not isinstance(root, dict):
            root = {}
        block = root.get("data")
        if not isinstance(block, dict):
            block = {}
            root["data"] = block
        return cls(data=block)

    def apply_defaults(self) -> None:
        """写入 ``settings_example`` 中与 data 相关的默认值（就地修改 ``self.data``）。"""
        d = self.data

        if "min_required_records" not in d:
            d["min_required_records"] = 100
        elif not isinstance(d["min_required_records"], int) or d["min_required_records"] <= 0:
            d["min_required_records"] = 100

        if "indicators" not in d:
            d["indicators"] = {}

        if "extra_required_data_sources" not in d:
            d["extra_required_data_sources"] = []
        elif not isinstance(d["extra_required_data_sources"], list):
            d["extra_required_data_sources"] = []

        base = d.get("base_required_data")
        if isinstance(base, dict) and base.get("params") is None:
            base["params"] = {}

    def validate(self) -> ValidationReport:
        """
        校验 data 契约；先 ``apply_defaults``，再 ``validate_data_config``。
        """
        result = SettingsBase.new_validation()
        self.apply_defaults()

        try:
            StrategySettingsDictModel.validate_data_config(self.data)
        except ValueError as e:
            SettingsBase.add_critical(
                result,
                "data",
                str(e),
                suggested_fix='参考 settings_example 的 "data"：至少包含 '
                '"base_required_data": {"params": {"term": "daily"}} 等',
            )

        return result

    def to_dict(self) -> Dict[str, Any]:
        """权威 ``data`` 块（深拷贝，不返回内部可变引用）。"""
        return self.deep_copy_dict(self.data)

    # --- 便捷访问（property，与旧 getter 语义一致）---

    @property
    def base_required_data(self) -> Dict[str, Any]:
        base = self.data.get("base_required_data")
        return base if isinstance(base, dict) else {}

    @property
    def extra_required_data_sources(self) -> List[Dict[str, Any]]:
        xs = self.data.get("extra_required_data_sources", [])
        if xs is None:
            return []
        if not isinstance(xs, list):
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
