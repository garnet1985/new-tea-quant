"""ML attribution primitives — XGBoost feature importance + optional SHAP."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

import numpy as np

try:
    import xgboost as xgb
except ImportError:  # pragma: no cover
    xgb = None  # type: ignore

try:
    import shap
except ImportError:  # pragma: no cover
    shap = None  # type: ignore

_MIN_SAMPLES_PER_FEATURE = 10


def _validate_inputs(
    feature_matrix: Sequence[Sequence[float]],
    feature_names: Sequence[str],
    target: Sequence[float],
    *,
    min_samples: int,
) -> Dict[str, Any]:
    n = len(feature_matrix)
    p = len(feature_names)
    if p == 0:
        return {"ok": False, "status": "skipped", "reason": "no_features"}
    if n != len(target):
        return {
            "ok": False,
            "status": "skipped",
            "reason": "length_mismatch",
            "n": n,
        }
    if n < min_samples:
        return {
            "ok": False,
            "status": "skipped",
            "reason": "insufficient_samples",
            "n": n,
            "min_samples": min_samples,
        }
    if n // p < _MIN_SAMPLES_PER_FEATURE:
        return {
            "ok": False,
            "status": "skipped",
            "reason": "insufficient_samples_per_feature",
            "n": n,
            "n_features": p,
            "min_ratio": _MIN_SAMPLES_PER_FEATURE,
        }
    return {"ok": True, "n": n, "n_features": p}


def _booster_scores(
    model: Any,
    feature_names: Sequence[str],
    importance_type: str,
) -> Dict[str, float]:
    raw = model.get_booster().get_score(importance_type=importance_type)
    out: Dict[str, float] = {}
    for index, name in enumerate(feature_names):
        value = raw.get(f"f{index}")
        if value is not None:
            out[str(name)] = float(value)
    return out


def _build_feature_importance(model: Any, feature_names: Sequence[str]) -> List[Dict[str, Any]]:
    gain = _booster_scores(model, feature_names, "gain")
    weight = _booster_scores(model, feature_names, "weight")
    cover = _booster_scores(model, feature_names, "cover")
    rows: List[Dict[str, Any]] = []
    for name in feature_names:
        rows.append(
            {
                "feature": name,
                "gain": gain.get(name, 0.0),
                "weight": weight.get(name, 0.0),
                "cover": cover.get(name, 0.0),
            }
        )
    rows.sort(key=lambda item: float(item["gain"]), reverse=True)
    return rows


def _compute_shap_summary(
    model: Any,
    features: np.ndarray,
    feature_names: Sequence[str],
) -> Dict[str, Any]:
    if shap is None:
        return {
            "status": "skipped",
            "reason": "missing_dependency",
            "dependency": "shap",
        }
    try:
        explainer = shap.TreeExplainer(model)
        values = explainer.shap_values(features)
        if isinstance(values, list):
            values = values[0]
        mean_abs = np.mean(np.abs(values), axis=0)
        ranked = sorted(
            [
                {"feature": name, "mean_abs_shap": float(value)}
                for name, value in zip(feature_names, mean_abs)
            ],
            key=lambda item: item["mean_abs_shap"],
            reverse=True,
        )
        return {"status": "ok", "mean_abs": ranked}
    except Exception:
        return {"status": "skipped", "reason": "shap_failed"}


def xgb_feature_importance(
    feature_matrix: Sequence[Sequence[float]],
    feature_names: Sequence[str],
    target: Sequence[float],
    *,
    min_samples: int = 500,
) -> Dict[str, Any]:
    validation = _validate_inputs(
        feature_matrix, feature_names, target, min_samples=min_samples
    )
    if not validation.get("ok"):
        return {key: value for key, value in validation.items() if key != "ok"}

    if xgb is None:
        return {
            "status": "skipped",
            "reason": "missing_dependency",
            "dependency": "xgboost",
        }

    n = int(validation["n"])
    p = int(validation["n_features"])
    features = np.asarray(feature_matrix, dtype=float)
    y = np.asarray(target, dtype=float)

    model = xgb.XGBRegressor(
        objective="reg:squarederror",
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=1,
    )
    try:
        model.fit(features, y)
    except Exception:
        return {"status": "skipped", "reason": "fit_failed", "n": n, "n_features": p}

    predictions = model.predict(features)
    ss_res = float(np.sum((y - predictions) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0.0 else 0.0

    shap_summary = _compute_shap_summary(model, features, feature_names)
    status = "ok" if shap_summary.get("status") == "ok" else "partial"

    return {
        "status": status,
        "n": n,
        "n_features": p,
        "model": "xgboost_regressor",
        "metrics": {"r_squared_in_sample": r_squared},
        "feature_importance": _build_feature_importance(model, feature_names),
        "shap": shap_summary,
    }


__all__ = ["xgb_feature_importance"]
