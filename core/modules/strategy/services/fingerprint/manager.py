#!/usr/bin/env python3
"""Fingerprint management primitives for strategy runtime."""

from __future__ import annotations

import copy
from typing import Any, Dict, List

from core.modules.strategy.engines.shared.data_classes.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.engines.simulator.enumerator.data_classes.fingerprint import (
    EnumeratorFingerprint,
)


class StrategyFingerprintManager:
    """Pure fingerprint construction and canonicalization rules."""

    @staticmethod
    def canonicalize_settings(raw_settings: Dict[str, Any]) -> Dict[str, Any]:
        validated = StrategySettings(raw_settings=dict(raw_settings or {}))
        report = validated.validate()
        if not report.is_usable():
            raise ValueError("settings validation failed")
        return validated.to_dict()

    @staticmethod
    def build_enumerator_fingerprint(
        *,
        flow_impl: Any,
        strategy_name: str,
        strategy_info: Any,
        settings_payload: Dict[str, Any],
        stock_ids: List[str],
    ) -> EnumeratorFingerprint:
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
    def build_scope_fingerprint_id(fp: EnumeratorFingerprint) -> str:
        return str(EnumeratorFingerprint.compute_enumerator_scope_fingerprint_id(fp) or "")


__all__ = ["StrategyFingerprintManager"]
