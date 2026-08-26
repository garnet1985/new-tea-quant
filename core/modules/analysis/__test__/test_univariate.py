"""Classical univariate stats implementation."""
from __future__ import annotations

import pytest

from core.modules.analysis import Analysis

pytestmark = pytest.mark.force_run


def test_quantile_buckets_splits_and_summarizes() -> None:
    values = [10.0, 12.0, 14.0, 16.0, 18.0, 20.0]
    rois = [0.10, 0.05, 0.02, -0.01, -0.03, -0.05]
    wins = [True, True, True, False, False, False]
    out = Analysis.Classical.quantile_buckets(
        values,
        rois,
        wins,
        n_buckets=3,
        min_bucket_size=2,
    )
    assert out["status"] == "ok"
    assert out["n_buckets"] == 3
    assert out["buckets"][0]["count"] == 2
    assert out["buckets"][-1]["win_rate"] == 0.0
    assert out["buckets"][0]["range"]["min"] == 10.0


def test_quantile_buckets_skips_when_below_min_bucket_size() -> None:
    out = Analysis.Classical.quantile_buckets([1.0, 2.0], [0.1, 0.2], [True, False], min_bucket_size=30)
    assert out["status"] == "skipped"
    assert out["reason"] == "insufficient_samples"


def test_spearman_perfect_monotone() -> None:
    x = [1.0, 2.0, 3.0, 4.0, 5.0]
    y = [2.0, 4.0, 6.0, 8.0, 10.0]
    out = Analysis.Classical.spearman_correlation(x, y)
    assert out["status"] == "ok"
    assert out["rho"] == pytest.approx(1.0)
    assert out["p_value"] == pytest.approx(0.0, abs=1e-9)


def test_spearman_requires_min_samples() -> None:
    out = Analysis.Classical.spearman_correlation([1.0, 2.0], [0.1, 0.2])
    assert out["status"] == "skipped"


def test_classical_namespace_delegates() -> None:
    out = Analysis.Classical.spearman_correlation([1.0, 2.0, 3.0], [3.0, 2.0, 1.0])
    assert out["status"] == "ok"
    assert out["rho"] == pytest.approx(-1.0)
