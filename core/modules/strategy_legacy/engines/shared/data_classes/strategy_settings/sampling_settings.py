#!/usr/bin/env python3
"""策略 sampling 配置块。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, FrozenSet

from .settings_base import SettingsBase, ValidationReport

KNOWN_STRATEGIES: FrozenSet[str] = frozenset(
    {"uniform", "stratified", "random", "continuous", "pool", "blacklist"}
)
_STRATEGY_SUBKEYS = frozenset(
    {"uniform", "stratified", "random", "continuous", "pool", "blacklist"}
)


@dataclass
class StrategySamplingSettings(SettingsBase):
    sampling: Dict[str, Any]

    @classmethod
    def from_strategy_root(cls, root: Dict[str, Any]) -> "StrategySamplingSettings":
        if not isinstance(root, dict):
            root = {}
        block = root.get("sampling")
        if not isinstance(block, dict):
            block = {}
            root["sampling"] = block
        return cls(sampling=block)

    def apply_defaults(self) -> None:
        self.sampling.setdefault("strategy", "continuous")
        self.sampling.setdefault("sampling_amount", 10)
        self.sampling.setdefault("use_sampling", False)
        self.sampling.setdefault("start_date", "")
        self.sampling.setdefault("end_date", "")

    def validate(self) -> ValidationReport:
        result = SettingsBase.new_validation()
        self.apply_defaults()
        us = self.sampling.get("use_sampling", False)
        if not isinstance(us, bool):
            SettingsBase.add_critical(result, "sampling.use_sampling", "use_sampling 必须为布尔")
        else:
            self.sampling["use_sampling"] = us
        raw_strategy = self.sampling.get("strategy", "continuous")
        strategy = raw_strategy.strip() if isinstance(raw_strategy, str) else ""
        strategy = strategy or "continuous"
        if strategy not in KNOWN_STRATEGIES:
            SettingsBase.add_critical(result, "sampling.strategy", f"未知采样策略: {raw_strategy!r}")
        else:
            self.sampling["strategy"] = strategy
        try:
            n = int(self.sampling.get("sampling_amount", 10))
            if n < 1:
                raise ValueError
        except (TypeError, ValueError):
            SettingsBase.add_critical(result, "sampling.sampling_amount", "sampling_amount 必须为正整数")

        for key in _STRATEGY_SUBKEYS:
            sub = self.sampling.get(key)
            if sub is None:
                continue
            if not isinstance(sub, dict):
                SettingsBase.add_critical(result, f"sampling.{key}", f"sampling.{key} 必须为 dict")

        for date_key in ("start_date", "end_date"):
            raw = self.sampling.get(date_key)
            if raw is None:
                continue
            text = str(raw).strip()
            if not text:
                continue
            if len(text) != 8 or not text.isdigit():
                SettingsBase.add_critical(
                    result,
                    f"sampling.{date_key}",
                    f"sampling.{date_key} 须为 YYYYMMDD 格式（8 位数字）或空字符串",
                )
        return result

    def to_dict(self) -> Dict[str, Any]:
        return self.deep_copy_dict(dict(self.sampling))

    def get_strategy(self) -> str:
        return str(self.sampling.get("strategy", "continuous") or "continuous")

    def get_sampling_amount(self) -> int:
        try:
            return max(int(self.sampling.get("sampling_amount", 10) or 10), 1)
        except (TypeError, ValueError):
            return 10

    def get_sub_config(self, key: str) -> Dict[str, Any]:
        sub = self.sampling.get(key)
        return sub if isinstance(sub, dict) else {}

    def get_use_sampling(self) -> bool:
        return bool(self.sampling.get("use_sampling", False))

    def get_start_date(self) -> str:
        return str(self.sampling.get("start_date", "") or "")

    def get_end_date(self) -> str:
        return str(self.sampling.get("end_date", "") or "")


__all__ = ["StrategySamplingSettings", "KNOWN_STRATEGIES"]
