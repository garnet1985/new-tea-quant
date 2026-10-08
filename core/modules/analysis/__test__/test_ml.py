"""ML XGBoost attribution implementation."""
from __future__ import annotations

import numpy as np
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


def _synthetic_win(n: int = 120) -> tuple:
    matrix = []
    wins = []
    for i in range(n):
        rsi = 10.0 + (i % 30)
        pe = 20.0 + (i % 17)
        matrix.append([rsi, pe])
        wins.append(rsi < 20)
    return matrix, ["rsi_value", "pe_value"], wins


def test_xgb_win_classifier_reports_auc() -> None:
    pytest.importorskip("shap")
    matrix, names, wins = _synthetic_win()
    out = Analysis.ML.xgb_win_classifier(matrix, names, wins, min_samples=80)
    assert out["status"] in ("ok", "partial")
    assert out["n"] == 120
    assert out.get("metrics", {}).get("auc") is not None
    assert out.get("metrics", {}).get("auc_train") is not None
    assert 0.0 <= float(out["metrics"]["accuracy"]) <= 1.0
    assert (out.get("split") or {}).get("kind") == "row"


def test_grouped_split_keeps_copies_together() -> None:
    from core.modules.analysis.core.ml.xgb_classifier import _split_indices

    groups = []
    y = []
    for i in range(40):
        key = f"60000{i % 20}.SH|2024010{i % 5 + 1}"
        groups.extend([key, key])
        y.extend([i % 2, i % 2])
    train, test, info = _split_indices(len(groups), 0.2, groups, np.asarray(y))
    assert info["kind"] == "grouped"
    train_g = {groups[int(i)] for i in train}
    test_g = {groups[int(i)] for i in test}
    assert train_g.isdisjoint(test_g)
    assert len(test) >= 8


def test_xgb_win_classifier_grouped_and_dependence() -> None:
    pytest.importorskip("shap")
    matrix = []
    names = ["rsi_value", "pe_value"]
    wins = []
    groups = []
    for i in range(60):
        rsi = 10.0 + (i % 30)
        pe = 15.0 + (i % 19)
        win = rsi < 22
        key = f"s{i}|20240101"
        for _copy in range(2):
            matrix.append([rsi, pe])
            wins.append(win)
            groups.append(key)
    out = Analysis.ML.xgb_win_classifier(
        matrix, names, wins, min_samples=80, groups=groups
    )
    assert out["status"] in ("ok", "partial")
    assert (out.get("split") or {}).get("kind") == "grouped"
    assert (out.get("split") or {}).get("n_groups") == 60
    assert out.get("metrics", {}).get("auc_train") is not None
    assert isinstance(out.get("dependence"), list)
    if out["status"] == "ok":
        assert out["dependence"]
        first = out["dependence"][0]
        assert first.get("feature") in names
        assert len(first.get("bins") or []) >= 3
