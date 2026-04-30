#!/usr/bin/env python3
"""Fingerprint usage workflows for runtime contexts."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .manager import StrategyFingerprintManager


class StrategyFingerprintRuntimeService:
    """Runtime-oriented wrappers around fingerprint manager primitives."""

    @staticmethod
    def build_ids_for_runtime_context(context: Any) -> Tuple[str, str]:
        fp = StrategyFingerprintManager.build_enumerator_fingerprint(
            flow_impl=context.flow._impl,
            strategy_name=context.strategy_name,
            strategy_info=context.strategy_info,
            settings_payload=context.settings_view.to_dict(),
            stock_ids=context.stock_list,
        )
        return str(fp.fingerprint_id or ""), StrategyFingerprintManager.build_scope_fingerprint_id(fp)

    @staticmethod
    def build_ids_from_request_fingerprint(request_fingerprint: Any) -> Tuple[str, str]:
        if request_fingerprint is None:
            return "", ""
        fp_id = str(getattr(request_fingerprint, "fingerprint_id", "") or "")
        if not fp_id:
            return "", ""
        return fp_id, StrategyFingerprintManager.build_scope_fingerprint_id(request_fingerprint)

    @staticmethod
    def build_fingerprint_for_snapshot_candidate(
        *,
        flow_ref: Any,
        strategy_name: str,
        strategy_info: Any,
        canonical_settings_payload: Dict[str, Any],
        stock_ids: List[str],
    ) -> Any:
        return StrategyFingerprintManager.build_enumerator_fingerprint(
            flow_impl=flow_ref._impl,
            strategy_name=strategy_name,
            strategy_info=strategy_info,
            settings_payload=canonical_settings_payload,
            stock_ids=stock_ids,
        )


__all__ = ["StrategyFingerprintRuntimeService"]
