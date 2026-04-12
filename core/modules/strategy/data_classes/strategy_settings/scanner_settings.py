#!/usr/bin/env python3
"""
策略 ``scanner`` 配置块（对应 ``settings_example`` 第 10) 节）。

整包 ``raw_settings`` 引用 + ``scanner`` 子树访问、默认值与适配器可用性校验（Warning）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Any, Dict, List, Literal, Union

from .settings_base import SettingsBase, ValidationReport

logger = logging.getLogger(__name__)


@dataclass
class StrategyScannerSettings(SettingsBase):
    """
    扫描器相关配置。

    - ``raw_settings``：完整策略 settings 字典
    - ``scanner``：通过属性访问 ``raw_settings["scanner"]``
    """

    raw_settings: Dict[str, Any]
    _scanner_validated: bool = field(default=False, repr=False)

    @property
    def scanner(self) -> Dict[str, Any]:
        block = self.raw_settings.get("scanner")
        if not isinstance(block, dict):
            block = {}
            self.raw_settings["scanner"] = block
        return block

    @classmethod
    def from_strategy_root(cls, root: Dict[str, Any]) -> StrategyScannerSettings:
        """挂载 ``scanner``；缺省或非 dict 时写入 ``{}``。"""
        if not isinstance(root, dict):
            root = {}
        block = root.get("scanner")
        if not isinstance(block, dict):
            block = {}
            root["scanner"] = block
        return cls(raw_settings=root)

    @classmethod
    def from_base_settings(cls, base_settings: "StrategySettings") -> StrategyScannerSettings:
        return cls.from_strategy_root(base_settings.raw_settings)

    def apply_defaults(self) -> None:
        """与 ``settings_example`` 中 ``scanner`` 默认值对齐。"""
        s = self.scanner
        if "max_workers" not in s:
            s["max_workers"] = "auto"
        if "adapters" not in s:
            s["adapters"] = ["console"]
        if "use_strict_previous_trading_day" not in s:
            s["use_strict_previous_trading_day"] = True
        if "max_cache_days" not in s:
            s["max_cache_days"] = 10
        if "watch_list" not in s:
            s["watch_list"] = ""

    def validate(self) -> ValidationReport:
        result = SettingsBase.new_validation()
        self.apply_defaults()
        self._normalize_fields()
        self._validate_adapters(result)
        SettingsBase.log_warnings(result, logger)
        self._scanner_validated = True
        return result

    def to_dict(self) -> Dict[str, Any]:
        self.apply_defaults()
        self._normalize_fields()
        return self.deep_copy_dict(dict(self.scanner))

    def _normalize_fields(self) -> None:
        s = self.scanner

        mw = s.get("max_workers", "auto")
        if mw == "auto" or mw is None:
            s["max_workers"] = "auto"
        else:
            try:
                s["max_workers"] = max(int(mw), 1)
            except (TypeError, ValueError):
                s["max_workers"] = "auto"

        adapter_config = s.get("adapters", [])
        if isinstance(adapter_config, str):
            s["adapters"] = [adapter_config] if adapter_config else ["console"]
        elif isinstance(adapter_config, list):
            s["adapters"] = adapter_config if adapter_config else ["console"]
        else:
            s["adapters"] = ["console"]

        ust = s.get("use_strict_previous_trading_day", True)
        s["use_strict_previous_trading_day"] = (
            ust if isinstance(ust, bool) else True
        )

        mcd = s.get("max_cache_days", 10)
        try:
            s["max_cache_days"] = max(int(mcd), 1)
        except (TypeError, ValueError):
            s["max_cache_days"] = 10

        wl = s.get("watch_list", "")
        s["watch_list"] = "" if wl is None else str(wl)

    def _validate_adapters(self, result: ValidationReport) -> None:
        from core.modules.adapter import validate_adapter

        adapter_names = self.adapter_names
        if not adapter_names:
            return

        for adapter_name in adapter_names:
            is_valid, error_message = validate_adapter(adapter_name)
            if not is_valid:
                SettingsBase.add_warning(
                    result,
                    f"scanner.adapters[{adapter_name}]",
                    f"适配器 '{adapter_name}' 不可用: {error_message}",
                    suggested_fix=(
                        f"请检查 userspace/adapters/{adapter_name}/adapter.py 是否存在，"
                        f"或从 scanner.adapters 中移除 '{adapter_name}'"
                    ),
                )

    @property
    def max_workers(self) -> Union[Literal["auto"], int]:
        mw = self.scanner.get("max_workers", "auto")
        if mw == "auto" or mw is None:
            return "auto"
        try:
            return max(int(mw), 1)
        except (TypeError, ValueError):
            return "auto"

    @property
    def adapter_names(self) -> List[str]:
        adapter_config = self.scanner.get("adapters", [])
        if isinstance(adapter_config, str):
            return [adapter_config] if adapter_config else ["console"]
        if isinstance(adapter_config, list):
            return adapter_config if adapter_config else ["console"]
        return ["console"]

    @property
    def use_strict_previous_trading_day(self) -> bool:
        v = self.scanner.get("use_strict_previous_trading_day", True)
        return bool(v) if isinstance(v, bool) else True

    @property
    def max_cache_days(self) -> int:
        try:
            return max(int(self.scanner.get("max_cache_days", 10)), 1)
        except (TypeError, ValueError):
            return 10

    @property
    def watch_list(self) -> str:
        v = self.scanner.get("watch_list", "")
        return "" if v is None else str(v)


ScannerSettings = StrategyScannerSettings
