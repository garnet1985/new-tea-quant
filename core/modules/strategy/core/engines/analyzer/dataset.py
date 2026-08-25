"""Extract aligned column vectors from ``source.json`` investments."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from .step_config import StepOutcomeConfig


def get_nested_field(row: Dict[str, Any], dotted: str) -> Any:
    current: Any = row
    for part in str(dotted or "").split("."):
        if not part:
            continue
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def as_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def is_win(result: Any, win_values: Sequence[str]) -> bool:
    text = str(result or "").strip().lower()
    return text in {str(v).strip().lower() for v in win_values}


def extract_capture_series(
    source: Dict[str, Any],
    capture_key: str,
    config: StepOutcomeConfig,
) -> Tuple[List[float], List[float], List[bool]]:
    values: List[float] = []
    rois: List[float] = []
    wins: List[bool] = []
    for entity in source.get("entities") or []:
        if not isinstance(entity, dict):
            continue
        for investment in entity.get("investments") or []:
            if not isinstance(investment, dict):
                continue
            capture = investment.get("capture")
            if not isinstance(capture, dict):
                continue
            x = as_float(capture.get(capture_key))
            roi = as_float(get_nested_field(investment, config.roi_field))
            if x is None or roi is None:
                continue
            values.append(x)
            rois.append(roi)
            wins.append(
                is_win(get_nested_field(investment, config.result_field), config.win_values)
            )
    return values, rois, wins


def count_investments(source: Dict[str, Any]) -> int:
    total = 0
    for entity in source.get("entities") or []:
        if not isinstance(entity, dict):
            continue
        investments = entity.get("investments") or []
        if isinstance(investments, list):
            total += len(investments)
    return total


def list_varying_numeric_capture_keys(decision_space: Dict[str, Any]) -> List[str]:
    capture = decision_space.get("capture")
    if not isinstance(capture, dict):
        return []
    keys: List[str] = []
    for key, summary in capture.items():
        if not isinstance(summary, dict):
            continue
        if summary.get("role") != "varying":
            continue
        if summary.get("dtype") != "numeric":
            continue
        keys.append(str(key))
    return sorted(keys)


def extract_feature_matrix(
    source: Dict[str, Any],
    feature_keys: Sequence[str],
    config: StepOutcomeConfig,
) -> Tuple[List[List[float]], List[float], List[bool]]:
    matrix: List[List[float]] = []
    rois: List[float] = []
    wins: List[bool] = []
    for entity in source.get("entities") or []:
        if not isinstance(entity, dict):
            continue
        for investment in entity.get("investments") or []:
            if not isinstance(investment, dict):
                continue
            capture = investment.get("capture")
            if not isinstance(capture, dict):
                continue
            row: List[float] = []
            for key in feature_keys:
                x = as_float(capture.get(key))
                if x is None:
                    row = []
                    break
                row.append(x)
            if len(row) != len(feature_keys):
                continue
            roi = as_float(get_nested_field(investment, config.roi_field))
            if roi is None:
                continue
            matrix.append(row)
            rois.append(roi)
            wins.append(
                is_win(get_nested_field(investment, config.result_field), config.win_values)
            )
    return matrix, rois, wins


__all__ = [
    "as_float",
    "count_investments",
    "extract_capture_series",
    "extract_feature_matrix",
    "get_nested_field",
    "is_win",
    "list_varying_numeric_capture_keys",
]
