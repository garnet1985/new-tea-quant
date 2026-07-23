"""Session-level ROI 分布：仅从内存中的 ``stock_summaries`` / ``investments`` 聚合，不扫磁盘逐股文件。

与 FED ``normalizePriceMetricsFromSummary`` 对齐：
- ``roi_percentile_values``：长度为 9，对应 10%～90% 分位，单位为 **百分比数值**（图表 ``{value}%``）。
- ``roi_bucket_*``：**固定档位**（0% 为界；负侧封顶 -100%；正侧含 >100% 尾档）。
- ``roi_std_pct``：单笔 ROI（百分比）的**样本标准差**（n≥2 时写入）。
- 分位与分桶默认仅含 **按 goal 规则退出** 的样本；``enumeration_end`` / ``backtest_end`` 强平单独计数。
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

_FORCED_EXIT_NAMES = frozenset({"enumeration_end", "backtest_end"})


def investment_final_exit_name(inv: Dict[str, Any]) -> str:
    """最后一笔 ``completed_targets`` 的退出原因（小写）。"""
    targets = inv.get("completed_targets") or []
    if not targets:
        return ""
    last = targets[-1]
    if not isinstance(last, dict):
        return ""
    return str(last.get("name") or "").lower()


def is_forced_exit_investment(inv: Dict[str, Any]) -> bool:
    """回测区间结束强制平仓，未按 goal 规则走完。"""
    return investment_final_exit_name(inv) in _FORCED_EXIT_NAMES


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


def collect_roi_percents_from_stock_summaries(
    stock_summaries: List[Dict[str, Any]],
) -> Tuple[List[float], int, int]:
    """
    收集计入 ROI 分布的样本。

    返回 ``(roi_pcts, truncated_exit_count, total_investment_count)``。
    排除 ``enumeration_end`` / ``backtest_end`` 与仍 ``open`` 的仓位。
    """
    rois: List[float] = []
    truncated = 0
    total = 0
    for row in stock_summaries:
        invs = row.get("investments")
        if not isinstance(invs, list):
            continue
        for inv in invs:
            if not isinstance(inv, dict):
                continue
            total += 1
            lifecycle = str(inv.get("lifecycle") or "").lower()
            if lifecycle == "open":
                continue
            if is_forced_exit_investment(inv):
                truncated += 1
                continue
            pct = _investment_roi_as_percent(inv)
            if pct is not None:
                rois.append(pct)
    return rois, truncated, total


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


def roi_distribution_session_fields(
    rois_pct: List[float],
    *,
    truncated_exit_count: int,
) -> Dict[str, Any]:
    """生成写入 ``0_session_summary.json`` / ``result_report.price_factor`` 的分位与分桶字段。"""
    out: Dict[str, Any] = {
        "roi_distribution_sample_count": len(rois_pct),
        "roi_truncated_exit_count": truncated_exit_count,
    }
    if not rois_pct:
        return out

    xs = sorted(rois_pct)
    pv = [round(_percentile_linear(xs, p), 2) for p in _PERCENT_POINTS]
    if len(pv) != 9 or any(not math.isfinite(x) for x in pv):
        return out

    labels_zh = [f"{p}%分位" for p in _PERCENT_POINTS]
    bucket_labels, counts = _fixed_roi_bins(rois_pct)

    out.update(
        {
            "roi_percentile_labels": labels_zh,
            "roi_percentile_values": pv,
            "roi_bucket_labels": bucket_labels,
            "roi_bucket_counts": counts,
            "roi_bucket_bin_count": len(bucket_labels),
        }
    )
    std_pct = _roi_sample_std_pct(rois_pct)
    if std_pct is not None:
        out["roi_std_pct"] = std_pct
    return out


__all__ = [
    "ROI_BUCKET_COUNT",
    "ROI_MAX_BIN_COUNT",
    "ROI_EQUAL_BIN_COUNT",
    "collect_roi_percents_from_stock_summaries",
    "investment_final_exit_name",
    "is_forced_exit_investment",
    "roi_distribution_session_fields",
    "_fixed_roi_bins",
]

ROI_MAX_BIN_COUNT = ROI_BUCKET_COUNT
ROI_EQUAL_BIN_COUNT = ROI_BUCKET_COUNT
