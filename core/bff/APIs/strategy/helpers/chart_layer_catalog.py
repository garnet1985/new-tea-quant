"""Strategy required data → chart layer role（单股详情分层展示）。

主图永远是 base OHLCV；required 按形态挂不同可视角色，不对齐成「再切一套 K」。
"""

from __future__ import annotations

from typing import Any, Dict, Optional

# 同源不同周期 OHLCV → 主图叠加（默认周/月收盘线）
VIZ_LINKED_OHLCV = "linked_ohlcv"
# 宏观低频序列 → 阶梯副轨
VIZ_MACRO_STEP = "macro_step"
# 时段状态（ST / 标签）→ 色带泳道
VIZ_STATE_LANE = "state_lane"
# 事件型（财报）→ 主图钉 + PIT 快照
VIZ_EVENT_PINS = "event_pins"

_ROLE_BY_KEY: Dict[str, str] = {
    "stock.kline.weekly": VIZ_LINKED_OHLCV,
    "stock.kline.monthly": VIZ_LINKED_OHLCV,
    "macro.gdp": VIZ_MACRO_STEP,
    "macro.cpi": VIZ_MACRO_STEP,
    "macro.ppi": VIZ_MACRO_STEP,
    "macro.pmi": VIZ_MACRO_STEP,
    "macro.lpr": VIZ_MACRO_STEP,
    "macro.shibor": VIZ_MACRO_STEP,
    "stock.st_periods": VIZ_STATE_LANE,
    "tag": VIZ_STATE_LANE,
    "stock.finance.quarterly": VIZ_EVENT_PINS,
}

_LABEL_BY_KEY: Dict[str, str] = {
    "stock.kline.weekly": "周收",
    "stock.kline.monthly": "月收",
    "macro.gdp": "GDP YoY",
    "macro.cpi": "CPI",
    "macro.ppi": "PPI",
    "macro.pmi": "PMI",
    "macro.lpr": "LPR",
    "macro.shibor": "Shibor",
    "stock.st_periods": "ST",
    "tag": "标签",
    "stock.finance.quarterly": "财报",
}


def resolve_viz_role(data_key: str) -> Optional[str]:
    key = str(data_key or "").strip().lower()
    if not key:
        return None
    if key in _ROLE_BY_KEY:
        return _ROLE_BY_KEY[key]
    if key.startswith("macro."):
        return VIZ_MACRO_STEP
    if key.startswith("stock.kline.") and key not in {
        "stock.kline.daily",
    }:
        return VIZ_LINKED_OHLCV
    return None


def layer_label(data_key: str) -> str:
    key = str(data_key or "").strip().lower()
    if key in _LABEL_BY_KEY:
        return _LABEL_BY_KEY[key]
    return key.split(".")[-1].upper() if key else "LAYER"


def date_to_quarter(yyyymmdd: str) -> str:
    raw = str(yyyymmdd or "").strip()
    if len(raw) < 6:
        return ""
    try:
        year = int(raw[:4])
        month = int(raw[4:6])
    except ValueError:
        return ""
    return f"{year}Q{(month - 1) // 3 + 1}"


def quarter_to_end_date(quarter: str) -> str:
    """季度末日历日 YYYYMMDD（再 asof 对齐到交易日）。"""
    q = str(quarter or "").strip().upper()
    if len(q) < 6 or "Q" not in q:
        return ""
    try:
        year = int(q[:4])
        n = int(q.split("Q", 1)[1])
    except ValueError:
        return ""
    ends = {1: "0331", 2: "0630", 3: "0930", 4: "1231"}
    suffix = ends.get(n)
    if not suffix:
        return ""
    return f"{year}{suffix}"


def layer_envelope(
    *,
    role: str,
    data_key: str,
    label: str = "",
    **payload: Any,
) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "role": role,
        "data_key": data_key,
        "label": label or layer_label(data_key),
    }
    out.update(payload)
    return out


__all__ = [
    "VIZ_EVENT_PINS",
    "VIZ_LINKED_OHLCV",
    "VIZ_MACRO_STEP",
    "VIZ_STATE_LANE",
    "date_to_quarter",
    "layer_envelope",
    "layer_label",
    "quarter_to_end_date",
    "resolve_viz_role",
]
