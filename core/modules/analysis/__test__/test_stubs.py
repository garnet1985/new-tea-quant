"""Analysis stats stub API (class-only Facade)."""
from __future__ import annotations

import pytest

from core.modules.analysis import Analysis

pytestmark = pytest.mark.force_run


def test_public_api_returns_structured_results() -> None:
    buckets = Analysis.Classical.quantile_buckets(
        [1.0, 2.0, 3.0, 4.0],
        [0.1, 0.2, 0.3, 0.4],
        [True, True, False, False],
        n_buckets=2,
        min_bucket_size=2,
    )
    assert buckets["status"] == "ok"
    corr = Analysis.Classical.spearman_correlation(
        [1.0, 2.0, 3.0, 4.0],
        [0.4, 0.3, 0.2, 0.1],
    )
    assert corr["status"] == "ok"
