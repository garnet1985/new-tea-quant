"""选装的 XGBoost / SHAP：缺了就跳过，不把归因打崩。"""
from __future__ import annotations

import builtins

import pytest

from core.modules.analysis.core.ml.availability import missing_ml_packages

pytestmark = pytest.mark.force_run


def test_missing_ml_packages_treats_load_errors_as_absent(monkeypatch):
    real_import = builtins.__import__

    def guarded(name, globals=None, locals=None, fromlist=(), level=0):
        if name in {"xgboost", "shap"}:
            raise OSError(f"cannot load {name}")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded)
    assert missing_ml_packages() == ["xgboost", "shap"]


def test_ml_appendix_skips_when_either_package_missing(monkeypatch):
    from core.modules.analysis.core.ml import availability

    monkeypatch.setattr(availability, "missing_ml_packages", lambda: ["shap"])
    skipped = availability.ml_appendix_skip(4)
    assert skipped is not None
    assert skipped["status"] == "skipped"
    assert skipped["reason"] == "missing_dependency"
    assert skipped["dependency"] == "shap"
    assert skipped["n_versions"] == 4


def test_ml_appendix_runs_when_packages_present(monkeypatch):
    from core.modules.analysis.core.ml import availability

    monkeypatch.setattr(availability, "missing_ml_packages", lambda: [])
    assert availability.ml_appendix_skip(2) is None


def test_win_classifier_skips_before_fit_when_ml_missing(monkeypatch):
    from core.modules.analysis.core.ml import xgb_classifier as mod

    monkeypatch.setattr(mod, "missing_ml_packages", lambda: ["xgboost", "shap"])
    out = mod.xgb_win_classifier(
        [[1.0, 2.0]] * 90,
        ["a", "b"],
        [True, False] * 45,
        min_samples=80,
    )
    assert out["status"] == "skipped"
    assert out["reason"] == "missing_dependency"
    assert out["dependency"] == "xgboost、shap"
