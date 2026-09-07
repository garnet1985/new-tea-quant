"""Classical univariate attribution primitives."""
from __future__ import annotations

import math
from statistics import median
from typing import Any, Dict, List, Optional, Sequence


def quantile_buckets(
    values: Sequence[float],
    outcomes_roi: Sequence[float],
    outcomes_is_win: Sequence[bool],
    *,
    n_buckets: int = 5,
    min_bucket_size: int = 30,
) -> Dict[str, Any]:
    n = len(values)
    if n == 0:
        return {"status": "skipped", "reason": "empty", "buckets": []}
    if len(outcomes_roi) != n or len(outcomes_is_win) != n:
        return {"status": "skipped", "reason": "length_mismatch", "buckets": []}

    if n < min_bucket_size:
        return {
            "status": "skipped",
            "reason": "insufficient_samples",
            "n": n,
            "min_bucket_size": min_bucket_size,
            "buckets": [],
        }

    bucket_count = min(max(int(n_buckets), 1), n)
    while bucket_count > 1 and n // bucket_count < min_bucket_size:
        bucket_count -= 1

    rows = sorted(
        zip(values, outcomes_roi, outcomes_is_win),
        key=lambda item: float(item[0]),
    )
    buckets: List[Dict[str, Any]] = []
    for index in range(bucket_count):
        start = index * n // bucket_count
        end = (index + 1) * n // bucket_count
        chunk = rows[start:end]
        if not chunk:
            continue
        xs = [float(item[0]) for item in chunk]
        rois = [float(item[1]) for item in chunk]
        wins = [bool(item[2]) for item in chunk]
        win_count = sum(1 for flag in wins if flag)
        buckets.append(
            {
                "bucket_id": index + 1,
                "label": f"Q{index + 1}",
                "range": {"min": min(xs), "max": max(xs)},
                "count": len(chunk),
                "win_rate": win_count / len(chunk),
                "mean_roi": sum(rois) / len(rois),
                "median_roi": float(median(rois)),
            }
        )

    if not buckets:
        return {"status": "skipped", "reason": "no_buckets", "buckets": []}

    return {
        "status": "ok",
        "n": n,
        "n_buckets": len(buckets),
        "buckets": buckets,
    }


def spearman_correlation(
    x: Sequence[float],
    y: Sequence[float],
) -> Dict[str, Any]:
    n = len(x)
    if n != len(y):
        return {
            "status": "skipped",
            "reason": "length_mismatch",
            "rho": None,
            "p_value": None,
            "n": n,
        }
    if n < 3:
        return {
            "status": "skipped",
            "reason": "insufficient_samples",
            "rho": None,
            "p_value": None,
            "n": n,
        }

    rho = _spearman_rho(x, y)
    return {
        "status": "ok",
        "rho": rho,
        "p_value": _spearman_p_value(rho, n),
        "n": n,
    }


def _spearman_rho(x: Sequence[float], y: Sequence[float]) -> float:
    rx = _rank_with_ties(x)
    ry = _rank_with_ties(y)
    return _pearson(rx, ry)


def _rank_with_ties(values: Sequence[float]) -> List[float]:
    indexed = sorted(enumerate(values), key=lambda item: float(item[1]))
    ranks = [0.0] * len(values)
    i = 0
    while i < len(indexed):
        j = i
        while j + 1 < len(indexed) and float(indexed[j + 1][1]) == float(indexed[i][1]):
            j += 1
        avg_rank = (i + j + 2) / 2.0
        for k in range(i, j + 1):
            ranks[indexed[k][0]] = avg_rank
        i = j + 1
    return ranks


def _pearson(xs: Sequence[float], ys: Sequence[float]) -> float:
    n = len(xs)
    if n == 0:
        return 0.0
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    den_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    if den_x == 0.0 or den_y == 0.0:
        return 0.0
    return num / (den_x * den_y)


def _spearman_p_value(rho: float, n: int) -> Optional[float]:
    if n < 3:
        return None
    clamped = max(min(float(rho), 1.0), -1.0)
    if abs(clamped) >= 1.0:
        return 0.0
    t_stat = clamped * math.sqrt((n - 2) / (1.0 - clamped * clamped))
    # Normal approximation for two-tailed test (exploratory; n often large in enum).
    z = abs(t_stat)
    return math.erfc(z / math.sqrt(2.0))


__all__ = ["quantile_buckets", "spearman_correlation"]
