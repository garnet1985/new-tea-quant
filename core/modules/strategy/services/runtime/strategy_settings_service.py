"""Workbench / 枚举器共用的 settings 规范化（API ↔ runtime 单一校验入口）。"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from .run_service import StrategyFingerprintManager


class StrategySettingsService:
    """围绕 ``StrategyFingerprintManager.canonicalize_settings`` 的薄封装。"""

    @staticmethod
    def runtime_to_api(runtime_settings: Dict[str, Any]) -> Dict[str, Any]:
        """runtime dict → 校验后的规范 dict（与 ``StrategySettings.to_dict()`` 对齐）。"""
        return StrategyFingerprintManager.canonicalize_settings(dict(runtime_settings or {}))

    @staticmethod
    def api_to_runtime(api_settings: Dict[str, Any]) -> Dict[str, Any]:
        """当前约定下 API 与 runtime 形态一致，仍走同一校验路径。"""
        return StrategyFingerprintManager.canonicalize_settings(dict(api_settings or {}))

    @staticmethod
    def canonicalize_api_settings(api_settings: Dict[str, Any]) -> Dict[str, Any]:
        return StrategyFingerprintManager.canonicalize_settings(dict(api_settings or {}))

    @staticmethod
    def normalize_runtime_settings(
        *,
        strategy_name: str,
        api_settings: Any,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        UI / DB 载荷 → 可写 userspace、可与 fingerprint 对齐的 runtime dict。

        返回 ``(normalized, None)``；失败时 ``(None, error_message)``。
        """
        if not isinstance(api_settings, dict):
            return None, "settings 必须为对象"
        try:
            merged = dict(api_settings)
            if strategy_name and not str(merged.get("name") or "").strip():
                merged["name"] = str(strategy_name)
            normalized = StrategyFingerprintManager.canonicalize_settings(merged)
            return normalized, None
        except ValueError as e:
            return None, str(e) or "settings 校验失败"
        except Exception as e:
            return None, str(e)


__all__ = ["StrategySettingsService"]
