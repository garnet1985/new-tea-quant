"""Session-level ROI 分布：仅从内存中的 ``stock_summaries`` / ``investments`` 聚合，不扫磁盘逐股文件。

与 FED ``normalizePriceMetricsFromSummary`` 对齐：
- ``roi_percentile_values``：长度为 9，对应 10%～90% 分位，单位为 **百分比数值**（图表 ``{value}%``）。
- ``roi_bucket_*``：**固定档位**（0% 为界；负侧封顶 -100%；正侧含 >100% 尾档）。
- ``roi_std_pct``：单笔 ROI（百分比）的**样本标准差**（n≥2 时写入）。
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

# 与前端默认 ``10%分位``…``90%分位`` 一致
_PERCENT_POINTS = [10, 20, 30, 40, 50, 60, 70, 80, 90]

# 固定分档总数（负 6 + 正 7）
ROI_BUCKET_COUNT = 13

# 负侧 6 档：单笔最多亏 100%，深亏合并 [-100%, -50%)
_ROI_NEG_BUCKET_LABELS = (
    "[-100%, -50%)",
    "[-50%, -30%)",
    "[-30%, -20%)",
    "[-20%, -10%)",
    "[-10%, -5%)",
    "[-5%, 0%)",
)

# 正侧：0–5、5–10、10–20、20–30、30–50、50–100、>100
_ROI_POS_BUCKET_LABELS = (
    "[0%, 5%)",
    "[5%, 10%)",
    "[10%, 20%)",
    "[20%, 30%)",
    "[30%, 50%)",
    "[50%, 100%)",
    ">100%",
)


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


def _roi_neg_bucket_index(x: float) -> int:
    """``x < 0``；更亏归入左端 ``[-100%, -50%)``。"""
    if x < -100.0:
        return 0
    if x < -50.0:
        return 0
    if x < -30.0:
        return 1
    if x < -20.0:
        return 2
    if x < -10.0:
        return 3
    if x < -5.0:
        return 4
    return 5


def _roi_pos_bucket_index(x: float) -> int:
    """``x >= 0``。"""
    if x >= 100.0:
        return 6
    if x >= 50.0:
        return 5
    if x >= 30.0:
        return 4
    if x >= 20.0:
        return 3
    if x >= 10.0:
        return 2
    if x >= 5.0:
        return 1
    return 0


def _fixed_roi_bins(rois_pct: List[float]) -> Tuple[List[str], List[int]]:
    """产品固定档位；始终返回全部标签（空档计数为 0）。"""
    labels = list(_ROI_NEG_BUCKET_LABELS) + list(_ROI_POS_BUCKET_LABELS)
    counts = [0] * len(labels)
    neg_n = len(_ROI_NEG_BUCKET_LABELS)
    for raw in rois_pct:
        x = float(raw)
        if x < 0:
            counts[_roi_neg_bucket_index(x)] += 1
        else:
            counts[neg_n + _roi_pos_bucket_index(x)] += 1
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
    bucket_labels, counts = _fixed_roi_bins(rois_pct)

    out: Dict[str, Any] = {
        "roi_percentile_labels": labels_zh,
        "roi_percentile_values": pv,
        "roi_bucket_labels": bucket_labels,
        "roi_bucket_counts": counts,
        "roi_bucket_bin_count": len(bucket_labels),
    }
    std_pct = _roi_sample_std_pct(rois_pct)
    if std_pct is not None:
        out["roi_std_pct"] = std_pct
    return out


__all__ = [
    "ROI_BUCKET_COUNT",
    "ROI_MAX_BIN_COUNT",
    "ROI_EQUAL_BIN_COUNT",
    "collect_roi_percents_from_stock_summaries",
    "roi_distribution_session_fields",
    "_fixed_roi_bins",
]

ROI_MAX_BIN_COUNT = ROI_BUCKET_COUNT
ROI_EQUAL_BIN_COUNT = ROI_BUCKET_COUNT
