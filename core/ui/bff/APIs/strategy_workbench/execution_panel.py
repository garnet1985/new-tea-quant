"""工作台执行面板三行摘要：由快照 ``result_report`` 派生。"""

from __future__ import annotations

from typing import Any, Dict, Optional


def _num(val: Any, default: float = 0.0) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _enum_line_from_result_report(rr: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    raw = rr.get("enum")
    if not isinstance(raw, dict) or not raw:
        return None
    metrics = raw.get("enumMetrics") if isinstance(raw.get("enumMetrics"), dict) else {}
    count = metrics.get("totalOpportunities")
    if count is None:
        return None
    try:
        return {"opportunities": int(count)}
    except (TypeError, ValueError):
        return None


def _price_line_from_result_report(rr: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    raw = rr.get("price_factor")
    if not isinstance(raw, dict) or not raw:
        return None
    metrics = raw.get("priceMetrics") if isinstance(raw.get("priceMetrics"), dict) else {}
    wr = _num(metrics.get("winRate"))
    ar = _num(metrics.get("avgRoi"))
    if wr == 0.0 and ar == 0.0 and not metrics:
        return None
    return {"winRate": round(wr, 2), "roi": round(ar, 2)}


def _capital_line_from_result_report(rr: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    raw = rr.get("portfolio")
    if not isinstance(raw, dict) or not raw:
        return None
    metrics = raw.get("capitalMetrics") if isinstance(raw.get("capitalMetrics"), dict) else {}
    profit = _num(metrics.get("totalProfit"))
    ic = _num(metrics.get("initialCapital"))
    ec = _num(metrics.get("finalEquity"))
    ret_pct = _num(metrics.get("totalReturnPct"))
    if ic == 0.0 and ec == 0.0 and profit == 0.0 and not metrics:
        return None
    return {
        "profit": profit,
        "retPct": round(ret_pct, 4),
        "initialCapital": ic,
        "endCapital": ec,
    }


def build_execution_panel_from_result_report(
    result_report: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """执行面板三行卡片摘要（``enum`` / ``price`` / ``capital``）；无槽位则对应键省略。"""
    rr = dict(result_report or {})
    out: Dict[str, Any] = {}
    enum_line = _enum_line_from_result_report(rr)
    if enum_line:
        out["enum"] = enum_line
    price_line = _price_line_from_result_report(rr)
    if price_line:
        out["price"] = price_line
    capital_line = _capital_line_from_result_report(rr)
    if capital_line:
        out["capital"] = capital_line
    return out


__all__ = ["build_execution_panel_from_result_report"]
