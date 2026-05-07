"""Session-level ROI 分布：仅从内存中的 ``stock_summaries`` / ``investments`` 聚合，不扫磁盘逐股文件。

与 FED ``normalizePriceMetricsFromSummary`` 对齐：
- ``roi_percentile_values``：长度为 9，对应 10%～90% 分位，单位为 **百分比数值**（图表 ``{value}%``）。
- ``roi_bucket_*``：在 **min(ROI)～max(ROI)** 上**等宽**分箱（默认 ``ROI_EQUAL_BIN_COUNT`` 份，可改为 5），
  将每笔投资落入对应区间计数；无额外产品预设档位。
- ``roi_std_pct``：单笔 ROI（百分比）的**样本标准差**（n≥2 时写入）。
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

# 与前端默认 ``10%分位``…``90%分位`` 一致
_PERCENT_POINTS = [10, 20, 30, 40, 50, 60, 70, 80, 90]

# 收益分布柱图：在 [min,max] 上等分档数（可改为 5）
ROI_EQUAL_BIN_COUNT = 7


def _investment_roi_as_percent(inv: Dict[str, Any]) -> Optional[float]:
    """单笔 ROI 转为百分比刻度（与 FED ``toRatioAsPercent`` 约定一致：小数为比率）。"""
    try:
        r = float(inv.get("roi", 0.0) or 0.0)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(r):
        return None
    if r == 0.0:
        return 0.0
    if abs(r) < 1.0:
        return r * 100.0
    return r


def collect_roi_percents_from_stock_summaries(stock_summaries: List[Dict[str, Any]]) -> List[float]:
    out: List[float] = []
    for row in stock_summaries:
        invs = row.get("investments")
        if not isinstance(invs, list):
            continue
        for inv in invs:
            if not isinstance(inv, dict):
                continue
            pct = _investment_roi_as_percent(inv)
            if pct is not None:
                out.append(pct)
    return out


def _percentile_linear(sorted_vals: List[float], p: float) -> float:
    """``p`` ∈ [0,100]。"""
    n = len(sorted_vals)
    if n == 0:
        return float("nan")
    if n == 1:
        return sorted_vals[0]
    k = (n - 1) * (p / 100.0)
    f = math.floor(k)
    c = min(math.ceil(k), n - 1)
    if f >= c:
        return sorted_vals[c]
    return sorted_vals[f] * (c - k) + sorted_vals[c] * (k - f)


def _roi_sample_std_pct(vals: List[float]) -> Optional[float]:
    """单笔 ROI（百分比）的样本标准差；至少 2 笔才有意义。"""
    n = len(vals)
    if n < 2:
        return None
    mean = sum(vals) / n
    var = sum((x - mean) ** 2 for x in vals) / (n - 1)
    if not math.isfinite(var) or var < 0:
        return None
    return round(math.sqrt(var), 2)


def _min_max_equal_bins(
    rois_pct: List[float],
    *,
    n_bins: int = ROI_EQUAL_BIN_COUNT,
) -> Tuple[List[str], List[int]]:
    """[min, max] 闭区间等分为 n_bins 段，左闭右开除最后一段含右端点；标签为百分点。"""
    mn = min(rois_pct)
    mx = max(rois_pct)
    n_bins = max(2, min(int(n_bins), 12))
    if mx - mn < 1e-9:
        # 全同值：拉成对称小窗再分箱，避免 0 宽度
        v = float(mn)
        half = max(abs(v) * 0.02, 2.0)
        lo, hi = v - half, v + half
    else:
        lo, hi = float(mn), float(mx)
    width = (hi - lo) / n_bins
    counts = [0] * n_bins
    for x in rois_pct:
        if x >= hi:
            idx = n_bins - 1
        elif x <= lo:
            idx = 0
        else:
            idx = min(n_bins - 1, int(math.floor((x - lo) / width + 1e-12)))
        counts[idx] += 1
    labels: List[str] = []
    for i in range(n_bins):
        a = lo + i * width
        b = lo + (i + 1) * width
        if i == n_bins - 1:
            labels.append(f"[{a:.1f}%, {b:.1f}%]")
        else:
            labels.append(f"[{a:.1f}%, {b:.1f}%)")
    return labels, counts


def roi_distribution_session_fields(rois_pct: List[float]) -> Dict[str, Any]:
    """生成写入 ``0_session_summary.json`` / ``result_report.price_factor`` 的分位与分桶字段。"""
    if not rois_pct:
        return {}
    xs = sorted(rois_pct)
    pv = [round(_percentile_linear(xs, p), 2) for p in _PERCENT_POINTS]
    if len(pv) != 9 or any(not math.isfinite(x) for x in pv):
        return {}

    labels_zh = [f"{p}%分位" for p in _PERCENT_POINTS]
    bucket_labels, counts = _min_max_equal_bins(rois_pct, n_bins=ROI_EQUAL_BIN_COUNT)

    out: Dict[str, Any] = {
        "roi_percentile_labels": labels_zh,
        "roi_percentile_values": pv,
        "roi_bucket_labels": bucket_labels,
        "roi_bucket_counts": counts,
        "roi_bucket_bin_count": ROI_EQUAL_BIN_COUNT,
    }
    std_pct = _roi_sample_std_pct(rois_pct)
    if std_pct is not None:
        out["roi_std_pct"] = std_pct
    return out


__all__ = [
    "ROI_EQUAL_BIN_COUNT",
    "collect_roi_percents_from_stock_summaries",
    "roi_distribution_session_fields",
]
