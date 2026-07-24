"""``settings.scanner`` — 扫描模式与缓存/adapter 配置。

本文件:
- ScannerSettings: 锚点严格模式、max_cache_days、adapter_names 等
  边界: 负责 scanner section；不负责 ScanDateResolver 或 BE 扫描
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from .settings_base import SettingsBase
from .validation_report import ValidationReport


@dataclass
class ScannerSettings(SettingsBase):
    """``settings.scanner`` — adapters / 严格交易日 / 缓存 / watch_list。"""

    raw_settings: Dict[str, Any]

    def _block(self) -> Dict[str, Any]:
        block = self.raw_settings.get("scanner")
        if not isinstance(block, dict):
            block = {}
            self.raw_settings["scanner"] = block
        return block

    @property
    def scanner(self) -> Dict[str, Any]:
        return dict(self._block())

    @property
    def adapter_names(self) -> List[str]:
        raw = self._block().get("adapters", ["console"])
        if isinstance(raw, str):
            return [raw] if raw.strip() else ["console"]
        if isinstance(raw, list):
            names = [str(x).strip() for x in raw if str(x).strip()]
            return names or ["console"]
        return ["console"]

    @property
    def use_strict_previous_trading_day(self) -> bool:
        v = self._block().get("use_strict_previous_trading_day", True)
        return bool(v) if isinstance(v, bool) else True

    @property
    def max_cache_days(self) -> int:
        try:
            return max(int(self._block().get("max_cache_days", 10)), 1)
        except (TypeError, ValueError):
            return 10

    @property
    def watch_list(self) -> str:
        v = self._block().get("watch_list", "")
        return "" if v is None else str(v)

    def set_use_strict_previous_trading_day(self, value: bool) -> None:
        self._block()["use_strict_previous_trading_day"] = bool(value)

    def apply_defaults(self) -> None:
        s = self._block()
        s.setdefault("adapters", ["console"])
        s.setdefault("use_strict_previous_trading_day", True)
        s.setdefault("max_cache_days", 10)
        s.setdefault("watch_list", "")
        self._normalize_fields()

    def validate(self) -> ValidationReport:
        report = SettingsBase.new_validation()
        if "scanner" in self.raw_settings and not isinstance(
            self.raw_settings.get("scanner"), dict
        ):
            SettingsBase.add_critical(
                report,
                "scanner",
                "scanner must be dict",
                suggested_fix="Set scanner to {} or omit",
            )
            return report

        self.apply_defaults()
        self._validate_adapters(report)
        return report

    def to_dict(self) -> Dict[str, Any]:
        self.apply_defaults()
        return SettingsBase.deep_copy_dict(dict(self._block()))

    def _normalize_fields(self) -> None:
        s = self._block()
        adapters = s.get("adapters", ["console"])
        if isinstance(adapters, str):
            s["adapters"] = [adapters] if adapters.strip() else ["console"]
        elif isinstance(adapters, list):
            names = [str(x).strip() for x in adapters if str(x).strip()]
            s["adapters"] = names or ["console"]
        else:
            s["adapters"] = ["console"]

        ust = s.get("use_strict_previous_trading_day", True)
        s["use_strict_previous_trading_day"] = ust if isinstance(ust, bool) else True

        try:
            s["max_cache_days"] = max(int(s.get("max_cache_days", 10)), 1)
        except (TypeError, ValueError):
            s["max_cache_days"] = 10

        wl = s.get("watch_list", "")
        s["watch_list"] = "" if wl is None else str(wl)

    def _validate_adapters(self, report: ValidationReport) -> None:
        from core.modules.adapter import validate_adapter

        for name in self.adapter_names:
            ok, err = validate_adapter(name)
            if not ok:
                SettingsBase.add_warning(
                    report,
                    f"scanner.adapters[{name}]",
                    f"适配器 '{name}' 不可用: {err}",
                )


__all__ = ["ScannerSettings"]
