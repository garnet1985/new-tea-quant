"""XGBoost 二分类：单笔是否赚钱 + SHAP。无业务、无 I/O。"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from .availability import missing_ml_packages
from .xgb_regressor import _validate_inputs

try:
    import xgboost as xgb
except Exception:  # pragma: no cover
    xgb = None  # type: ignore

_TEST_RATIO = 0.2
_DIRECTION_FLAT = 0.005
_DEPENDENCE_TOP = 3
_DEPENDENCE_BINS = 5


def xgb_win_classifier(
    feature_matrix: Sequence[Sequence[float]],
    feature_names: Sequence[str],
    is_win: Sequence[bool],
    *,
    min_samples: int = 80,
    test_ratio: float = _TEST_RATIO,
    groups: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    missing = missing_ml_packages()
    if missing or xgb is None:
        names = missing or ["xgboost"]
        return {
            "status": "skipped",
            "reason": "missing_dependency",
            "dependency": "、".join(names),
        }

    validation = _validate_inputs(
        feature_matrix, feature_names, [1.0 if flag else 0.0 for flag in is_win],
        min_samples=min_samples,
    )
    if not validation.get("ok"):
        return {key: value for key, value in validation.items() if key != "ok"}

    n = int(validation["n"])
    p = int(validation["n_features"])
    features = np.asarray(feature_matrix, dtype=float)
    y = np.asarray([1 if flag else 0 for flag in is_win], dtype=int)
    names = [str(name) for name in feature_names]

    train_idx, test_idx, split_info = _split_indices(n, test_ratio, groups, y)
    x_train, y_train = features[train_idx], y[train_idx]
    x_test, y_test = features[test_idx], y[test_idx]
    if len(set(y_train.tolist())) < 2 or len(y_test) < 8:
        return {
            "status": "skipped",
            "reason": "insufficient_class_balance",
            "n": n,
            "n_features": p,
        }

    model = xgb.XGBClassifier(
        objective="binary:logistic",
        eval_metric="auc",
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=1,
    )
    try:
        model.fit(x_train, y_train)
    except Exception:
        return {"status": "skipped", "reason": "fit_failed", "n": n, "n_features": p}

    proba_test = _positive_proba(model, x_test)
    proba_train = _positive_proba(model, x_train)
    pred = (proba_test >= 0.5).astype(int)
    auc_test = _roc_auc(y_test, proba_test)
    auc_train = _roc_auc(y_train, proba_train)
    accuracy = float(np.mean(pred == y_test)) if len(y_test) else None

    shap_values = _shap_matrix(model, features)
    shap_summary = _shap_summary(shap_values, names)
    directions: List[Dict[str, Any]] = []
    dependence: List[Dict[str, Any]] = []
    if shap_values is not None:
        directions = _shap_directions(features, names, shap_values)
        dependence = _shap_dependence(features, names, shap_values, shap_summary)

    status = "ok" if shap_summary.get("status") == "ok" else "partial"
    return {
        "status": status,
        "n": n,
        "n_features": p,
        "n_train": int(len(train_idx)),
        "n_test": int(len(test_idx)),
        "model": "xgboost_classifier",
        "target": "roi_positive",
        "split": split_info,
        "metrics": {
            "auc": auc_test,
            "auc_test": auc_test,
            "auc_train": auc_train,
            "accuracy": accuracy,
        },
        "shap": shap_summary,
        "directions": directions,
        "dependence": dependence,
    }


def _split_indices(
    n: int,
    test_ratio: float,
    groups: Optional[Sequence[str]] = None,
    y: Optional[np.ndarray] = None,
) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    grouped = _grouped_split(n, test_ratio, groups)
    if grouped is not None:
        train_idx, test_idx, info = grouped
        if _split_usable(train_idx, test_idx, y):
            return train_idx, test_idx, info
    train_idx, test_idx = _row_split(n, test_ratio)
    return train_idx, test_idx, {
        "kind": "row",
        "n_groups": n,
        "n_train_groups": int(len(train_idx)),
        "n_test_groups": int(len(test_idx)),
    }


def _grouped_split(
    n: int,
    test_ratio: float,
    groups: Optional[Sequence[str]],
) -> Optional[Tuple[np.ndarray, np.ndarray, Dict[str, Any]]]:
    keys = _group_keys(n, groups)
    if keys is None:
        return None
    unique: List[str] = []
    seen = set()
    for key in keys:
        if key in seen:
            continue
        seen.add(key)
        unique.append(key)
    if len(unique) < 10:
        return None
    rng = np.random.RandomState(42)
    order = rng.permutation(len(unique))
    n_test_g = max(2, int(round(len(unique) * float(test_ratio))))
    n_test_g = min(n_test_g, len(unique) - 2)
    test_groups = {unique[int(i)] for i in order[:n_test_g]}
    train_idx = np.array(
        [i for i, key in enumerate(keys) if key not in test_groups],
        dtype=int,
    )
    test_idx = np.array(
        [i for i, key in enumerate(keys) if key in test_groups],
        dtype=int,
    )
    info = {
        "kind": "grouped",
        "n_groups": len(unique),
        "n_train_groups": len(unique) - len(test_groups),
        "n_test_groups": len(test_groups),
    }
    return train_idx, test_idx, info


def _group_keys(n: int, groups: Optional[Sequence[str]]) -> Optional[List[str]]:
    if groups is None or len(groups) != n:
        return None
    keys: List[str] = []
    named = 0
    for i, group in enumerate(groups):
        text = str(group or "").strip()
        if text:
            named += 1
            keys.append(text)
        else:
            keys.append(f"row:{i}")
    if named < 10:
        return None
    return keys


def _row_split(n: int, test_ratio: float) -> Tuple[np.ndarray, np.ndarray]:
    rng = np.random.RandomState(42)
    order = rng.permutation(n)
    n_test = max(8, int(round(n * float(test_ratio))))
    n_test = min(n_test, n - 16) if n > 24 else max(1, n // 5)
    test_idx = np.sort(order[:n_test])
    train_idx = np.sort(order[n_test:])
    return train_idx, test_idx


def _split_usable(
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    y: Optional[np.ndarray],
) -> bool:
    if len(test_idx) < 8 or len(train_idx) < 16:
        return False
    if y is None:
        return True
    return len(set(y[train_idx].tolist())) >= 2 and len(set(y[test_idx].tolist())) >= 2


def _positive_proba(model: Any, features: np.ndarray) -> np.ndarray:
    raw = model.predict_proba(features)
    if raw.ndim == 2 and raw.shape[1] >= 2:
        return np.asarray(raw[:, 1], dtype=float)
    return np.asarray(raw, dtype=float).reshape(-1)


def _roc_auc(y_true: np.ndarray, y_score: np.ndarray) -> Optional[float]:
    y_true = np.asarray(y_true, dtype=int)
    y_score = np.asarray(y_score, dtype=float)
    n_pos = int(np.sum(y_true == 1))
    n_neg = int(np.sum(y_true == 0))
    if n_pos <= 0 or n_neg <= 0:
        return None
    order = np.argsort(y_score, kind="mergesort")
    sorted_scores = y_score[order]
    ranks = np.empty(len(y_score), dtype=float)
    i = 0
    n = len(y_score)
    while i < n:
        j = i + 1
        while j < n and sorted_scores[j] == sorted_scores[i]:
            j += 1
        avg = 0.5 * ((i + 1) + j)
        ranks[order[i:j]] = avg
        i = j
    sum_pos = float(ranks[y_true == 1].sum())
    return (sum_pos - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)


def _shap_matrix(model: Any, features: np.ndarray) -> Optional[np.ndarray]:
    try:
        import shap
    except Exception:
        return None
    try:
        explainer = shap.TreeExplainer(model)
        values = explainer.shap_values(features)
        if isinstance(values, list):
            values = values[1] if len(values) > 1 else values[0]
        values = np.asarray(values, dtype=float)
        if values.ndim == 3:
            values = values[:, :, 1]
        if values.shape[0] != features.shape[0]:
            return None
        return values
    except Exception:
        return None


def _shap_summary(
    values: Optional[np.ndarray],
    feature_names: Sequence[str],
) -> Dict[str, Any]:
    if values is None:
        return {
            "status": "skipped",
            "reason": "missing_dependency",
            "dependency": "shap",
        }
    mean_abs = np.mean(np.abs(values), axis=0)
    ranked = sorted(
        [
            {"feature": name, "mean_abs_shap": float(score)}
            for name, score in zip(feature_names, mean_abs)
        ],
        key=lambda item: item["mean_abs_shap"],
        reverse=True,
    )
    return {"status": "ok", "mean_abs": ranked}


def _shap_directions(
    features: np.ndarray,
    feature_names: Sequence[str],
    values: np.ndarray,
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for i, name in enumerate(feature_names):
        col = features[:, i]
        shap_col = values[:, i]
        finite = np.isfinite(col) & np.isfinite(shap_col)
        if int(np.sum(finite)) < 12:
            continue
        xs = col[finite]
        sh = shap_col[finite]
        lo_cut = float(np.quantile(xs, 0.33))
        hi_cut = float(np.quantile(xs, 0.67))
        low = sh[xs <= lo_cut]
        high = sh[xs >= hi_cut]
        if len(low) < 4 or len(high) < 4:
            continue
        low_mean = float(np.mean(low))
        high_mean = float(np.mean(high))
        if abs(low_mean) < _DIRECTION_FLAT and abs(high_mean) < _DIRECTION_FLAT:
            sign = "flat"
        elif low_mean > high_mean:
            sign = "low_positive"
        else:
            sign = "high_positive"
        out.append(
            {
                "feature": str(name),
                "low": {"threshold": lo_cut, "mean_shap": low_mean, "n": int(len(low))},
                "high": {"threshold": hi_cut, "mean_shap": high_mean, "n": int(len(high))},
                "sign": sign,
            }
        )
    return out


def _shap_dependence(
    features: np.ndarray,
    feature_names: Sequence[str],
    values: np.ndarray,
    shap_summary: Dict[str, Any],
) -> List[Dict[str, Any]]:
    ranked = shap_summary.get("mean_abs") if isinstance(shap_summary, dict) else None
    order = [
        str(item.get("feature"))
        for item in (ranked or [])
        if isinstance(item, dict) and item.get("feature")
    ]
    if not order:
        order = [str(name) for name in feature_names]
    index = {str(name): i for i, name in enumerate(feature_names)}
    out: List[Dict[str, Any]] = []
    for name in order:
        if len(out) >= _DEPENDENCE_TOP:
            break
        i = index.get(name)
        if i is None:
            continue
        bins = _dependence_bins(features[:, i], values[:, i])
        if len(bins) < 3:
            continue
        peak = max(bins, key=lambda item: float(item.get("mean_shap") or 0.0))
        out.append({"feature": name, "bins": bins, "peak": peak})
    return out


def _dependence_bins(col: np.ndarray, shap_col: np.ndarray) -> List[Dict[str, Any]]:
    finite = np.isfinite(col) & np.isfinite(shap_col)
    if int(np.sum(finite)) < 20:
        return []
    xs = col[finite]
    sh = shap_col[finite]
    if len(set(np.round(xs, 8).tolist())) < 3:
        return []
    edges = np.unique(np.quantile(xs, np.linspace(0.0, 1.0, _DEPENDENCE_BINS + 1)))
    if len(edges) < 3:
        return []
    bins: List[Dict[str, Any]] = []
    last = len(edges) - 1
    for i in range(last):
        lo = float(edges[i])
        hi = float(edges[i + 1])
        if i == last - 1:
            mask = (xs >= lo) & (xs <= hi)
        else:
            mask = (xs >= lo) & (xs < hi)
        if int(np.sum(mask)) < 4:
            continue
        bins.append(
            {
                "lo": lo,
                "hi": hi,
                "mid": (lo + hi) / 2.0,
                "mean_shap": float(np.mean(sh[mask])),
                "n": int(np.sum(mask)),
            }
        )
    return bins


__all__ = ["xgb_win_classifier"]
