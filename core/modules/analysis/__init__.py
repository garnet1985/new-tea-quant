"""Analysis module — stats/ML primitives (no business I/O)."""

from .analysis import (
    Analysis,
    Classical,
    ML,
    compare_run_summaries,
    logistic_win,
    ols_weighted_roi,
    quantile_buckets,
    spearman_correlation,
    xgb_feature_importance,
)

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
