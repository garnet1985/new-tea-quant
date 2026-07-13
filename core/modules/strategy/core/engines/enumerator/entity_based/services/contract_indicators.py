"""Batch-apply declared indicators onto loaded per-entity contracts (once per job)."""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from core.modules.indicator import IndicatorService

logger = logging.getLogger(__name__)


def _indicator_field_name(name: str, params: Dict[str, Any]) -> str:
    name = name.lower()
    length = params.get("length")
    if length is not None and isinstance(length, (int, float, str)):
        return f"{name}{int(length)}"
    parts = [name]
    for key in sorted(params.keys()):
        value = params[key]
        if isinstance(value, (int, float, str)):
            parts.append(f"{key}{value}")
    return "_".join(parts)


def _apply_indicators_to_rows(
    rows: List[Dict[str, Any]],
    indicators_cfg: Dict[str, Any],
) -> None:
    for name, cfg, result in IndicatorService.compute_batch(rows, indicators_cfg):
        try:
            if isinstance(result, list):
                field = _indicator_field_name(name, cfg)
                for rec, val in zip(rows, result):
                    rec[field] = val
            elif isinstance(result, dict):
                for key, series in result.items():
                    field = _indicator_field_name(f"{name}_{key}", cfg)
                    for rec, val in zip(rows, series):
                        rec[field] = val
        except Exception as exc:
            logger.error(
                "写入指标失败: indicator=%s params=%s error=%s",
                name,
                cfg,
                exc,
            )


def apply_indicators_to_contracts(
    entity_contracts: Dict[str, Any],
    entity_shared: Dict[str, Dict[str, Any]],
) -> None:
    """Precompute indicators on full kline rows (legacy ``apply_indicators`` parity)."""
    for data_key, params_dict in entity_shared.items():
        indicators_cfg = params_dict.get("indicators") or {}
        if not indicators_cfg:
            continue
        contract = entity_contracts.get(data_key)
        if contract is None or not getattr(contract, "is_loaded", False):
            continue
        data = getattr(contract, "data", None)
        if not isinstance(data, dict):
            continue
        for entity_id, rows in data.items():
            if not isinstance(rows, list) or not rows:
                continue
            _apply_indicators_to_rows(rows, indicators_cfg)


__all__ = ["apply_indicators_to_contracts"]
