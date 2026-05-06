#!/usr/bin/env python3
"""
运行期指纹服务层（依赖 StrategySettings / flow_impl）。

与 DbCache 无关；位于 ``strategy.services.launcher``。说明见同包 ``__init__.py``。
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional, Tuple

from core.modules.strategy.engines.shared.data_classes.strategy_settings.strategy_settings import (
    StrategySettings,
)

from .run_types import StrategyRunFingerprint


class StrategyFingerprintManager:
    """规范化 settings 与构建运行指纹。"""

    @staticmethod
    def canonicalize_settings(raw_settings: Dict[str, Any]) -> Dict[str, Any]:
        validated = StrategySettings(raw_settings=dict(raw_settings or {}))
        report = validated.validate()
        if not report.is_usable():
            raise ValueError("settings validation failed")
        return validated.to_dict()

    @staticmethod
    def build_run_fingerprint(
        *,
        flow_impl: Any,
        strategy_name: str,
        strategy_info: Any,
        settings_payload: Dict[str, Any],
        stock_ids: List[str],
    ) -> StrategyRunFingerprint:
        worker_ref = flow_impl.resolve_worker_blueprint(
            strategy_name=strategy_name,
            strategy_info=strategy_info,
        )
        return flow_impl.build_request_fingerprint(
            strategy_name=strategy_name,
            settings_payload=copy.deepcopy(settings_payload),
            stock_ids=stock_ids,
            worker_ref=worker_ref,
        )

    @staticmethod
    def build_scope_fingerprint_id(fp: StrategyRunFingerprint) -> str:
        return str(StrategyRunFingerprint.compute_scope_fingerprint_id(fp) or "")


class StrategyFingerprintRuntimeService:
    """与 runtime context 配合的指纹辅助。"""

    @staticmethod
    def build_ids_for_runtime_context(context: Any) -> Tuple[str, str]:
        fp = StrategyFingerprintManager.build_run_fingerprint(
            flow_impl=context.flow._impl,
            strategy_name=context.strategy_name,
            strategy_info=context.strategy_info,
            settings_payload=context.settings_view.to_dict(),
            stock_ids=context.stock_list,
        )
        return str(fp.fingerprint_id or ""), StrategyFingerprintManager.build_scope_fingerprint_id(
            fp
        )


class StrategySettingsService:
    """UI / DB settings → ``StrategyFingerprintManager`` 规范化（单一入口）。"""

    @staticmethod
    def normalize_runtime_settings(
        *,
        strategy_name: str,
        api_settings: Any,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
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


__all__ = [
    "StrategyFingerprintManager",
    "StrategyFingerprintRuntimeService",
    "StrategySettingsService",
]
