"""工作台执行面板三行摘要：由快照 ``result_report`` 派生，供 V2-01 / V2-08 与前端展示。"""

from __future__ import annotations

from typing import Any, Dict, Optional


def _num(val: Any, default: float = 0.0) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _enum_line_from_result_report(rr: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    from core.modules.strategy.services.cache.simulator_res_db_cache.report_slot_disk_hydrate import (
        attach_enum_opportunities_field,
        enum_opportunity_count_from_slot,
    )

    raw = rr.get("enum")
    if not isinstance(raw, dict) or not raw:
        return None
    merged = attach_enum_opportunities_field(dict(raw))
    count = enum_opportunity_count_from_slot(merged)
    if count is None:
        return None
    return {"opportunities": int(count)}


def _price_line_from_result_report(rr: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    raw = rr.get("price_factor")
    if not isinstance(raw, dict) or not raw:
        return None
    wr = _num(raw.get("win_rate", raw.get("winRate")))
    ar = _num(raw.get("avg_roi", raw.get("roi", raw.get("avgRoi"))))
    if ar != 0.0 and abs(ar) < 1.0:
        ar = round(ar * 100.0, 2)
    else:
        ar = round(ar, 2)
    if wr == 0.0 and ar == 0.0 and not raw.get("win_rate") and not raw.get("avg_roi"):
        return None
    return {"winRate": round(wr, 2), "roi": ar}


def _capital_line_from_result_report(rr: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    raw = rr.get("capital_allocation")
    if not isinstance(raw, dict) or not raw:
        return None
    profit = _num(raw.get("total_profit", raw.get("profit")))
    ic = _num(raw.get("initial_capital", raw.get("initialCapital")))
    ec = _num(raw.get("final_total_equity", raw.get("end_capital", raw.get("endCapital"))))
    if ec == 0.0 and (ic != 0.0 or profit != 0.0):
        ec = ic + profit
    ret_pct = _num(
        raw.get("total_return", raw.get("retPct", raw.get("return_pct", raw.get("ret_pct"))))
    )
    if ret_pct != 0.0 and abs(ret_pct) <= 1.0:
        ret_pct = round(ret_pct * 100.0, 4)
    else:
        ret_pct = round(ret_pct, 4)
    if ic == 0.0 and ec == 0.0 and profit == 0.0:
        return None
    return {
        "profit": profit,
        "retPct": ret_pct,
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
