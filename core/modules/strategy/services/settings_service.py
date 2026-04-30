#!/usr/bin/env python3
"""Strategy settings canonicalization and validation service."""

from __future__ import annotations

from typing import Any, Dict, Tuple

from core.modules.strategy.engines.shared.data_classes.strategy_settings.strategy_settings import (
    StrategySettings,
)


class StrategySettingsService:
    """Single source of truth for settings shape conversion/validation."""

    @staticmethod
    def api_to_runtime(api_settings: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(api_settings, dict):
            return {}
        runtime = dict(api_settings)
        meta = runtime.pop("meta", None)
        if isinstance(meta, dict):
            runtime["name"] = meta.get("name", runtime.get("name", ""))
            runtime["description"] = meta.get("description", runtime.get("description", ""))
            runtime["is_enabled"] = bool(meta.get("is_enabled", runtime.get("is_enabled", False)))
        return runtime

    @staticmethod
    def runtime_to_api(runtime_settings: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(runtime_settings, dict):
            return {}
        validated = StrategySettings(raw_settings=dict(runtime_settings))
        report = validated.validate()
        if not report.is_usable():
            return {}
        return validated.to_dict()

    @classmethod
    def canonicalize_api_settings(cls, api_settings: Dict[str, Any]) -> Dict[str, Any]:
        runtime = cls.api_to_runtime(api_settings)
        return cls.runtime_to_api(runtime)

    @classmethod
    def normalize_runtime_settings(
        cls,
        *,
        strategy_name: str,
        api_settings: Dict[str, Any],
    ) -> Tuple[Dict[str, Any] | None, str]:
        if not isinstance(api_settings, dict):
            return None, "请求体缺少 settings 或类型错误"
        runtime = cls.api_to_runtime(api_settings)
        runtime["name"] = strategy_name
        validated = StrategySettings(raw_settings=dict(runtime))
        report = validated.validate()
        if not report.is_usable():
            critical_errors = [
                f"{item.get('field_path', 'unknown')}: {item.get('message', '')}"
                for item in (report.errors or [])
                if item.get("level") == "critical"
            ]
            detail = "；".join(critical_errors) if critical_errors else "settings 校验失败"
            return None, detail
        normalized = validated.to_dict()
        normalized["name"] = strategy_name
        return normalized, ""


__all__ = ["StrategySettingsService"]
