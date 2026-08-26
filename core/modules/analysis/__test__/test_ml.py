"""ML XGBoost attribution implementation."""
from __future__ import annotations

import pytest

from core.modules.analysis import Analysis

pytestmark = pytest.mark.force_run

xgboost = pytest.importorskip("xgboost")


def _synthetic_ml(n: int = 520) -> tuple:
    matrix = []
    target = []
    for i in range(n):
        a = 10.0 + (i % 11)
        b = 0.5 + (i % 7) * 0.1
        matrix.append([a, b])
        target.append(0.002 * a - 0.01 * b + (0.001 if i % 2 else -0.001))
    return matrix, ["feat_a", "feat_b"], target


def test_xgb_feature_importance_fits_and_ranks_features() -> None:
    matrix, names, target = _synthetic_ml()
    out = Analysis.ML.xgb_feature_importance(matrix, names, target, min_samples=500)
    assert out["status"] in ("ok", "partial")
    assert out["n"] == 520
    assert len(out["feature_importance"]) == 2
    assert out["feature_importance"][0]["gain"] >= 0.0
    assert out["metrics"]["r_squared_in_sample"] is not None


def test_xgb_skips_below_min_samples() -> None:
    matrix, names, target = _synthetic_ml(n=100)
    out = Analysis.ML.xgb_feature_importance(matrix, names, target, min_samples=500)
    assert out["status"] == "skipped"
    assert out["reason"] == "insufficient_samples"


def test_classical_namespace_delegates_xgb() -> None:
    matrix, names, target = _synthetic_ml()
    out = Analysis.ML.xgb_feature_importance(matrix, names, target, min_samples=500)
    assert out["status"] in ("ok", "partial")
