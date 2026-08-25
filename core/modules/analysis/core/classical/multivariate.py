"""Classical multivariate attribution primitives."""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

try:
    from sklearn.linear_model import LogisticRegression
except ImportError:  # pragma: no cover
    LogisticRegression = None  # type: ignore

_MIN_SAMPLES_PER_FEATURE = 10


def _validate_inputs(
    feature_matrix: Sequence[Sequence[float]],
    feature_names: Sequence[str],
    target: Sequence[Any],
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


def _as_matrix(feature_matrix: Sequence[Sequence[float]]) -> np.ndarray:
    return np.asarray(feature_matrix, dtype=float)


def _t_test_p_value(t_stat: float, df: int) -> Optional[float]:
    if df <= 0:
        return None
    try:
        from scipy import stats

        return float(2.0 * stats.t.sf(abs(t_stat), df))
    except ImportError:
        z = abs(float(t_stat))
        return math.erfc(z / math.sqrt(2.0))


def _normal_two_tail_p(z_stat: float) -> Optional[float]:
    z = abs(float(z_stat))
    return math.erfc(z / math.sqrt(2.0))


def _log_likelihood(y: np.ndarray, probs: np.ndarray) -> float:
    clipped = np.clip(probs, 1e-12, 1.0 - 1e-12)
    return float(np.sum(y * np.log(clipped) + (1.0 - y) * np.log(1.0 - clipped)))


def logistic_win(
    feature_matrix: Sequence[Sequence[float]],
    feature_names: Sequence[str],
    is_win: Sequence[bool],
    *,
    min_samples: int = 200,
) -> Dict[str, Any]:
    validation = _validate_inputs(
        feature_matrix, feature_names, is_win, min_samples=min_samples
    )
    if not validation.get("ok"):
        return {key: value for key, value in validation.items() if key != "ok"}

    if LogisticRegression is None:
        return {
            "status": "skipped",
            "reason": "missing_dependency",
            "dependency": "scikit-learn",
        }

    n = int(validation["n"])
    p = int(validation["n_features"])
    y = np.asarray(is_win, dtype=int)
    if len(np.unique(y)) < 2:
        return {"status": "skipped", "reason": "single_class", "n": n, "n_features": p}

    design = np.column_stack([np.ones(n), _as_matrix(feature_matrix)])
    try:
        model = LogisticRegression(
            fit_intercept=False,
            penalty=None,
            solver="lbfgs",
            max_iter=1000,
        )
        model.fit(design, y)
    except (ValueError, np.linalg.LinAlgError):
        return {"status": "skipped", "reason": "fit_failed", "n": n, "n_features": p}

    coefs = model.coef_.ravel()
    probs = np.clip(model.predict_proba(design)[:, 1], 1e-9, 1.0 - 1e-9)
    weights = probs * (1.0 - probs)
    try:
        hessian = design.T @ (design * weights[:, None])
        cov = np.linalg.inv(hessian)
        se = np.sqrt(np.clip(np.diag(cov), 0.0, None))
    except np.linalg.LinAlgError:
        return {"status": "skipped", "reason": "singular_matrix", "n": n, "n_features": p}

    p_null = float(y.mean())
    ll_full = _log_likelihood(y, probs)
    ll_null = _log_likelihood(y, np.full(n, p_null))
    pseudo_r2 = 1.0 - ll_full / ll_null if ll_null != 0.0 else None

    coefficients: List[Dict[str, Any]] = []
    for index, name in enumerate(feature_names):
        coef_index = index + 1
        z_stat = float(coefs[coef_index] / se[coef_index]) if se[coef_index] > 0 else 0.0
        coef_value = float(coefs[coef_index])
        coefficients.append(
            {
                "feature": name,
                "coef": coef_value,
                "std_err": float(se[coef_index]),
                "z_stat": z_stat,
                "p_value": _normal_two_tail_p(z_stat),
                "odds_ratio": float(math.exp(coef_value)),
            }
        )

    return {
        "status": "ok",
        "n": n,
        "n_features": p,
        "intercept": float(coefs[0]),
        "coefficients": coefficients,
        "pseudo_r2": pseudo_r2,
    }


def ols_weighted_roi(
    feature_matrix: Sequence[Sequence[float]],
    feature_names: Sequence[str],
    roi: Sequence[float],
    *,
    min_samples: int = 200,
) -> Dict[str, Any]:
    validation = _validate_inputs(feature_matrix, feature_names, roi, min_samples=min_samples)
    if not validation.get("ok"):
        return {key: value for key, value in validation.items() if key != "ok"}

    n = int(validation["n"])
    p = int(validation["n_features"])
    y = np.asarray(roi, dtype=float)
    design = np.column_stack([np.ones(n), _as_matrix(feature_matrix)])

    beta, _, rank, _ = np.linalg.lstsq(design, y, rcond=None)
    if rank < p + 1:
        return {"status": "skipped", "reason": "rank_deficient", "n": n, "n_features": p}

    df = n - p - 1
    if df <= 0:
        return {
            "status": "skipped",
            "reason": "insufficient_degrees_of_freedom",
            "n": n,
            "n_features": p,
        }

    resid = y - design @ beta
    sse = float(np.dot(resid, resid))
    try:
        xtx_inv = np.linalg.inv(design.T @ design)
    except np.linalg.LinAlgError:
        return {"status": "skipped", "reason": "singular_matrix", "n": n, "n_features": p}

    s2 = sse / df
    se = np.sqrt(np.clip(np.diag(xtx_inv) * s2, 0.0, None))

    sst = float(np.sum((y - y.mean()) ** 2))
    r_squared = 1.0 - sse / sst if sst > 0.0 else 0.0
    adj_r_squared = 1.0 - (1.0 - r_squared) * (n - 1) / df

    coefficients: List[Dict[str, Any]] = []
    for index, name in enumerate(feature_names):
        coef_index = index + 1
        t_stat = float(beta[coef_index] / se[coef_index]) if se[coef_index] > 0 else 0.0
        coefficients.append(
            {
                "feature": name,
                "coef": float(beta[coef_index]),
                "std_err": float(se[coef_index]),
                "t_stat": t_stat,
                "p_value": _t_test_p_value(t_stat, df),
            }
        )

    return {
        "status": "ok",
        "n": n,
        "n_features": p,
        "intercept": float(beta[0]),
        "coefficients": coefficients,
        "r_squared": r_squared,
        "adj_r_squared": adj_r_squared,
    }


__all__ = ["logistic_win", "ols_weighted_roi"]
