"""Classical multivariate stats implementation."""
from __future__ import annotations

import pytest

from core.modules.analysis import Analysis

pytestmark = pytest.mark.force_run


def _synthetic_multivariate(n: int = 220) -> tuple:
    matrix = []
    wins = []
    rois = []
    for i in range(n):
        a = 10.0 + (i % 11)
        b = 0.5 + (i % 7) * 0.1
        matrix.append([a, b])
        wins.append(i % 3 != 0)
        rois.append(0.002 * a - 0.01 * b + (0.001 if i % 2 else -0.001))
    names = ["feat_a", "feat_b"]
    return matrix, names, wins, rois


def test_logistic_win_fits_and_returns_coefficients() -> None:
    matrix, names, wins, _ = _synthetic_multivariate()
    out = Analysis.Classical.logistic_win(matrix, names, wins, min_samples=200)
    assert out["status"] == "ok"
    assert out["n"] == 220
    assert out["n_features"] == 2
    assert len(out["coefficients"]) == 2
    assert out["coefficients"][0]["feature"] == "feat_a"
    assert out["coefficients"][0]["p_value"] is not None


def test_ols_weighted_roi_fits_and_returns_r_squared() -> None:
    matrix, names, _, rois = _synthetic_multivariate()
    out = Analysis.Classical.ols_weighted_roi(matrix, names, rois, min_samples=200)
    assert out["status"] == "ok"
    assert out["r_squared"] is not None
    assert out["adj_r_squared"] is not None
    assert out["coefficients"][0]["coef"] != 0.0


def test_multivariate_skips_below_min_samples() -> None:
    matrix, names, wins, rois = _synthetic_multivariate(n=50)
    logistic = Analysis.Classical.logistic_win(matrix, names, wins, min_samples=200)
    ols = Analysis.Classical.ols_weighted_roi(matrix, names, rois, min_samples=200)
    assert logistic["status"] == "skipped"
    assert logistic["reason"] == "insufficient_samples"
    assert ols["status"] == "skipped"


def test_logistic_skips_single_class() -> None:
    matrix, names, _, _ = _synthetic_multivariate(n=220)
    wins = [True] * 220
    out = Analysis.Classical.logistic_win(matrix, names, wins, min_samples=200)
    assert out["status"] == "skipped"
    assert out["reason"] == "single_class"


def test_classical_namespace_delegates_multivariate() -> None:
    matrix, names, wins, rois = _synthetic_multivariate()
    logistic = Analysis.Classical.logistic_win(matrix, names, wins, min_samples=200)
    ols = Analysis.Classical.ols_weighted_roi(matrix, names, rois, min_samples=200)
    assert logistic["status"] == "ok"
    assert ols["status"] == "ok"
