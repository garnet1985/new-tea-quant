"""``settings.scanner`` — 扫描模式与缓存 / post_process 配置。

本文件:
- ScannerSettings: 锚点严格模式、max_cache_days、post_process 等
  边界: 负责 scanner section；不负责 ScanDateResolver 或 BE 扫描
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from .settings_base import SettingsBase
from .validation_report import ValidationReport

DEFAULT_POST_PROCESS = "console"


@dataclass
class ScannerSettings(SettingsBase):
    """``settings.scanner`` — post_process / 严格交易日 / 缓存 / watch_list。"""

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
    def post_process(self) -> str:
        raw = self._block().get("post_process", DEFAULT_POST_PROCESS)
        name = str(raw or "").strip()
        return name or DEFAULT_POST_PROCESS

    @property
    def use_strict_previous_trading_day(self) -> bool:
        v = self._block().get("use_strict_previous_trading_day", True)
        return bool(v) if isinstance(v, bool) else True

    @property
    def max_cache_days(self) -> int:
        """Scan 日期版本保留上限；默认取 ``data.json`` retention.scan_results_max_versions。"""
        default = self._system_scan_max_versions()
        if "max_cache_days" not in self._block():
            return default
        try:
            return max(int(self._block().get("max_cache_days")), 1)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _system_scan_max_versions() -> int:
        from core.infra.project_context import ProjectContext

        return ProjectContext.config.get_scan_results_max_versions()

    @property
    def watch_list(self) -> str:
        v = self._block().get("watch_list", "")
        return "" if v is None else str(v)

    def set_use_strict_previous_trading_day(self, value: bool) -> None:
        self._block()["use_strict_previous_trading_day"] = bool(value)

    def apply_defaults(self) -> None:
        s = self._block()
        s.setdefault("post_process", DEFAULT_POST_PROCESS)
        s.setdefault("use_strict_previous_trading_day", True)
        s.setdefault("max_cache_days", self._system_scan_max_versions())
        s.setdefault("watch_list", "")
        # 清理过时字段
        s.pop("adapters", None)
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
        self._validate_post_process(report)
        return report

    def to_dict(self) -> Dict[str, Any]:
        self.apply_defaults()
        return SettingsBase.deep_copy_dict(dict(self._block()))

    def _normalize_fields(self) -> None:
        s = self._block()
        s.pop("adapters", None)
        pp = str(s.get("post_process") or "").strip()
        s["post_process"] = pp or DEFAULT_POST_PROCESS

        ust = s.get("use_strict_previous_trading_day", True)
        s["use_strict_previous_trading_day"] = ust if isinstance(ust, bool) else True

        default_max = self._system_scan_max_versions()
        try:
            s["max_cache_days"] = max(int(s.get("max_cache_days", default_max)), 1)
        except (TypeError, ValueError):
            s["max_cache_days"] = default_max

        wl = s.get("watch_list", "")
        s["watch_list"] = "" if wl is None else str(wl)

    def _validate_post_process(self, report: ValidationReport) -> None:
        from core.modules.post_process import PostProcess

        key = self.post_process
        ok, err = PostProcess.validate_post_processor(key)
        if not ok:
            SettingsBase.add_warning(
                report,
                f"scanner.post_process[{key}]",
                f"后续处理 '{key}' 不可用: {err}",
            )


__all__ = ["DEFAULT_POST_PROCESS", "ScannerSettings"]
