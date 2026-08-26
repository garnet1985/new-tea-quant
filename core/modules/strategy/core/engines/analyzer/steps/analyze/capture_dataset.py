"""Map ``source.json`` investments → aligned series for attribution (strategy schema)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from core.modules.analysis import Analysis

from ...support.step_outcome import StepOutcomeConfig


class CaptureDataset:
    """Business: read prepare-step ``source.json`` shape + step outcome fields."""

    @staticmethod
    def nested_field(row: Dict[str, Any], dotted: str) -> Any:
        current: Any = row
        for part in str(dotted or "").split("."):
            if not part:
                continue
            if not isinstance(current, dict):
                return None
            current = current.get(part)
        return current

    @classmethod
    def as_float(cls, value: Any) -> Optional[float]:
        return Analysis.Classical.coerce_float(value)

    @classmethod
    def is_win(cls, result: Any, win_values: Sequence[str]) -> bool:
        text = str(result or "").strip().lower()
        return text in {str(v).strip().lower() for v in win_values}

    @classmethod
    def extract_capture_series(
        cls,
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
                x = cls.as_float(capture.get(capture_key))
                roi = cls.as_float(cls.nested_field(investment, config.roi_field))
                if x is None or roi is None:
                    continue
                values.append(x)
                rois.append(roi)
                wins.append(
                    cls.is_win(
                        cls.nested_field(investment, config.result_field),
                        config.win_values,
                    )
                )
        return values, rois, wins

    @staticmethod
    def count_investments(source: Dict[str, Any]) -> int:
        total = 0
        for entity in source.get("entities") or []:
            if not isinstance(entity, dict):
                continue
            investments = entity.get("investments") or []
            if isinstance(investments, list):
                total += len(investments)
        return total

    @staticmethod
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

    @classmethod
    def extract_feature_matrix(
        cls,
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
                    x = cls.as_float(capture.get(key))
                    if x is None:
                        row = []
                        break
                    row.append(x)
                if len(row) != len(feature_keys):
                    continue
                roi = cls.as_float(cls.nested_field(investment, config.roi_field))
                if roi is None:
                    continue
                matrix.append(row)
                rois.append(roi)
                wins.append(
                    cls.is_win(
                        cls.nested_field(investment, config.result_field),
                        config.win_values,
                    )
                )
        return matrix, rois, wins
