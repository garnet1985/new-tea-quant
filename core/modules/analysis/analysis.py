"""Analysis Facade — stats/ML primitives for attribution (no I/O)."""
from __future__ import annotations

from core.modules.analysis.core.classical.multivariate import (
    logistic_win,
    ols_weighted_roi,
)
from core.modules.analysis.core.classical.run_comparison import compare_run_summaries
from core.modules.analysis.core.classical.univariate import (
    quantile_buckets,
    spearman_correlation,
)
from core.modules.analysis.core.ml.xgb_regressor import xgb_feature_importance


class Classical:
    """Classical statistics attribution primitives."""

    quantile_buckets = staticmethod(quantile_buckets)
    spearman_correlation = staticmethod(spearman_correlation)
    logistic_win = staticmethod(logistic_win)
    ols_weighted_roi = staticmethod(ols_weighted_roi)
    compare_run_summaries = staticmethod(compare_run_summaries)


class ML:
    """Machine-learning attribution primitives (later track)."""

    xgb_feature_importance = staticmethod(xgb_feature_importance)


class Analysis:
    """Attribution stats toolbox facade."""

    Classical = Classical
    ML = ML


__all__ = [
    "Analysis",
    "Classical",
    "ML",
    "compare_run_summaries",
    "logistic_win",
    "ols_weighted_roi",
    "quantile_buckets",
    "spearman_correlation",
    "xgb_feature_importance",
]
