#!/usr/bin/env python3
"""Scanner settings data class."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Any, Dict, List, Literal, Union

from core.modules.strategy.engines.shared.data_classes.strategy_settings.settings_base import (
    SettingsBase,
    ValidationReport,
)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.modules.strategy.engines.shared.data_classes.strategy_settings.strategy_settings import (
        StrategySettings,
    )

logger = logging.getLogger(__name__)


@dataclass
class StrategyScannerSettings(SettingsBase):
    raw_settings: Dict[str, Any]
    _scanner_validated: bool = field(default=False, repr=False)

    @property
    def scanner(self) -> Dict[str, Any]:
        return SettingsBase.ensure_dict_block(self.raw_settings, "scanner")

    @classmethod
    def from_strategy_root(cls, root: Dict[str, Any]) -> "StrategyScannerSettings":
        if not isinstance(root, dict):
            root = {}
        SettingsBase.ensure_dict_block(root, "scanner")
        return cls(raw_settings=root)

    @classmethod
    def from_base_settings(cls, base_settings: StrategySettings) -> "StrategyScannerSettings":
        return cls.from_strategy_root(base_settings.raw_settings)

    def apply_defaults(self) -> None:
        s = self.scanner
        s.setdefault("max_workers", "auto")
        s.setdefault("adapters", ["console"])
        s.setdefault("use_strict_previous_trading_day", True)
        s.setdefault("max_cache_days", 10)
        s.setdefault("watch_list", "")

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
        SettingsBase.normalize_max_workers_inplace(s, "max_workers")

        adapter_config = s.get("adapters", [])
        if isinstance(adapter_config, str):
            s["adapters"] = [adapter_config] if adapter_config else ["console"]
        elif isinstance(adapter_config, list):
            s["adapters"] = adapter_config if adapter_config else ["console"]
        else:
            s["adapters"] = ["console"]

        ust = s.get("use_strict_previous_trading_day", True)
        s["use_strict_previous_trading_day"] = ust if isinstance(ust, bool) else True

        mcd = s.get("max_cache_days", 10)
        try:
            s["max_cache_days"] = max(int(mcd), 1)
        except (TypeError, ValueError):
            s["max_cache_days"] = 10

        wl = s.get("watch_list", "")
        s["watch_list"] = "" if wl is None else str(wl)

    def _validate_adapters(self, result: ValidationReport) -> None:
        from core.modules.adapter import validate_adapter

        for adapter_name in self.adapter_names:
            is_valid, error_message = validate_adapter(adapter_name)
            if not is_valid:
                SettingsBase.add_warning(
                    result,
                    f"scanner.adapters[{adapter_name}]",
                    f"适配器 '{adapter_name}' 不可用: {error_message}",
                )

    @property
    def max_workers(self) -> Union[Literal["auto"], int]:
        return SettingsBase.parse_max_workers(self.scanner.get("max_workers", "auto"))

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

__all__ = ["StrategyScannerSettings", "ScannerSettings"]
