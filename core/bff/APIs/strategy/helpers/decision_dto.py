"""决策者会话 → FED DTO（页面字段在此命名，不进 Strategy facade）。"""

from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List, Optional, Sequence

_OHLCV_KEYS = ("date", "open", "high", "low", "close", "volume")
_OSCILLATOR_PREFIXES = (
    "rsi",
    "stoch",
    "willr",
    "mfi",
    "cmo",
    "cci",
    "uo",
    "aroon",
)
_INDICATOR_LINE_COLORS = (
    "#64B5F6",
    "#BA68C8",
    "#4DD0E1",
    "#AED581",
    "#FF8A65",
    "#F06292",
)


def _json_number(raw: Any) -> Optional[float]:
    """浏览器 JSON.parse 不能吃 NaN/Inf；与 price factor 单股图同一条。"""
    if raw is None:
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if math.isnan(value) or math.isinf(value):
        return None
    return value


def _round_price(raw: Any) -> Optional[float]:
    value = _json_number(raw)
    if value is None:
        return None
    return round(value, 2)


def _sanitize_cell(raw: Any) -> Any:
    if isinstance(raw, bool) or raw is None:
        return raw
    if isinstance(raw, (int, float)):
        return _json_number(raw)
    return raw


def _sanitize_row(row: Any) -> Dict[str, Any]:
    if not isinstance(row, dict):
        return {}
    return {str(key): _sanitize_cell(value) for key, value in row.items()}


def _normalize_ymd(raw: Any) -> str:
    text = str(raw or "").strip().replace("-", "")
    if len(text) >= 8 and text[:8].isdigit():
        return text[:8]
    return ""


def _candle_from_row(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    date = _normalize_ymd(row.get("date"))
    open_ = _round_price(row.get("open"))
    close = _round_price(row.get("close"))
    if not date or open_ is None or close is None:
        return None
    high = _round_price(row.get("high"))
    low = _round_price(row.get("low"))
    if high is None:
        high = close
    if low is None:
        low = close
    if high < low:
        high, low = low, high
    return {"date": date, "open": open_, "close": close, "high": high, "low": low}


def _indicator_panel(column: str) -> str:
    key = str(column or "").lower()
    return "oscillator" if any(key.startswith(prefix) for prefix in _OSCILLATOR_PREFIXES) else "overlay"


def _indicator_series_from_rows(
    columns: Sequence[str],
    rows: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    extra = [
        str(col).strip()
        for col in columns
        if str(col).strip() and str(col).strip() not in _OHLCV_KEYS
    ]
    series: List[Dict[str, Any]] = []
    for index, col in enumerate(extra):
        data = [_json_number(row.get(col)) for row in rows]
        if not any(value is not None for value in data):
            continue
        series.append(
            {
                "key": col,
                "label": col.upper(),
                "panel": _indicator_panel(col),
                "color": _INDICATOR_LINE_COLORS[index % len(_INDICATOR_LINE_COLORS)],
                "data": data,
            }
        )
    return series


def _stats_dict(raw: Any) -> Optional[Dict[str, Any]]:
    if raw is None:
        return None
    if isinstance(raw, dict):
        return {
            "sample_size": int(raw.get("sample_size") or 0),
            "wins": int(raw.get("wins") or 0),
            "win_rate": _json_number(raw.get("win_rate")),
            "avg_roi": _json_number(raw.get("avg_roi")),
        }
    to_dict = getattr(raw, "to_dict", None)
    if callable(to_dict):
        return _stats_dict(to_dict())
    return {
        "sample_size": int(getattr(raw, "sample_size", 0) or 0),
        "wins": int(getattr(raw, "wins", 0) or 0),
        "win_rate": _json_number(getattr(raw, "win_rate", None)),
        "avg_roi": _json_number(getattr(raw, "avg_roi", None)),
    }


def _lot_size(engine: Any, entity_id: str) -> Optional[int]:
    alloc = getattr(engine, "allocation", None)
    fn = getattr(alloc, "min_buy_shares", None)
    if not callable(fn):
        return None
    try:
        n = int(fn(str(entity_id or "")) or 0)
    except (TypeError, ValueError):
        return None
    return n if n > 0 else None


def _suggested_kelly_shares(engine: Any, opp: Any) -> Optional[int]:
    stats = getattr(opp, "ticker_stats", None)
    if stats is None:
        return None
    sample = int(getattr(stats, "sample_size", 0) or 0)
    win_rate = getattr(stats, "win_rate", None)
    if sample <= 0 or win_rate is None:
        return None
    alloc = getattr(engine, "allocation", None)
    fn = getattr(alloc, "suggest_kelly_shares", None)
    account = getattr(engine, "account", None)
    if not callable(fn) or account is None:
        return None
    try:
        return int(
            fn(
                account,
                float(getattr(opp, "entry_price_raw", 0.0) or 0.0),
                str(getattr(opp, "entity_id", "") or ""),
                float(win_rate),
            )
        )
    except (TypeError, ValueError):
        return None


def _status_tags(raw: Any) -> List[str]:
    if not isinstance(raw, (list, tuple)):
        return []
    out: List[str] = []
    for item in raw:
        tag = str(item or "").strip().lower()
        if tag and tag not in out:
            out.append(tag)
    return out


def _opportunity_dict(opp: Any, engine: Any = None) -> Dict[str, Any]:
    ticker = getattr(opp, "ticker_stats", None)
    entity_id = str(getattr(opp, "entity_id", "") or "")
    return {
        "local_id": int(getattr(opp, "local_id", 0) or 0),
        "entity_id": entity_id,
        "name": str(getattr(opp, "name", "") or ""),
        "status_tags": _status_tags(getattr(opp, "status_tags", None)),
        "entry_price": float(getattr(opp, "entry_price_raw", 0.0) or 0.0),
        "stats": _stats_dict(ticker),
        "lot_size": _lot_size(engine, entity_id),
        "suggested_shares": _suggested_kelly_shares(engine, opp),
    }


def _draft_lines(engine: Any) -> List[Dict[str, Any]]:
    draft = dict(getattr(engine, "draft", None) or {})
    lines: List[Dict[str, Any]] = []
    lookup = getattr(engine, "opportunity_by_local", None)
    for lid in sorted(draft):
        shares = int(draft[lid])
        opp = lookup(int(lid)) if callable(lookup) else None
        if opp is None:
            continue
        price = float(getattr(opp, "entry_price_raw", 0.0) or 0.0)
        lines.append(
            {
                "local_id": int(getattr(opp, "local_id", lid) or lid),
                "entity_id": str(getattr(opp, "entity_id", "") or ""),
                "name": str(getattr(opp, "name", "") or ""),
                "status_tags": _status_tags(getattr(opp, "status_tags", None)),
                "shares": shares,
                "entry_price": price,
                "notional": float(shares) * price,
            }
        )
    return lines


def _exit_dict(notice: Any) -> Dict[str, Any]:
    return {
        "date": str(getattr(notice, "date", "") or ""),
        "entity_id": str(getattr(notice, "entity_id", "") or ""),
        "name": str(getattr(notice, "name", "") or ""),
        "status_tags": _status_tags(getattr(notice, "status_tags", None)),
        "shares": int(getattr(notice, "shares", 0) or 0),
        "profit": float(getattr(notice, "profit", 0.0) or 0.0),
        "goal_names": str(getattr(notice, "goal_names", "") or ""),
        "reason": str(getattr(notice, "reason", "") or ""),
    }


def session_index_row(row: Dict[str, Any]) -> Dict[str, Any]:
    raw = dict(row or {})
    return {
        "dm_id": str(raw.get("dm_id") or ""),
        "status": str(raw.get("status") or ""),
        "current_date": str(raw.get("current_date") or ""),
        "updated_at": str(raw.get("updated_at") or ""),
    }


def session_list_message(payload: Dict[str, Any]) -> Dict[str, Any]:
    body = dict(payload or {})
    return {
        "version_id": str(body.get("version_id") or ""),
        "strategy_key": str(body.get("strategy_key") or ""),
        "has_portfolio": bool(body.get("has_portfolio")),
        "sessions": [session_index_row(row) for row in (body.get("sessions") or [])],
    }


def session_snapshot(
    engine: Any,
    *,
    exits: Optional[Sequence[Any]] = None,
) -> Dict[str, Any]:
    """一局现场：现金 / 机会 / 草稿。holdings 与 info 另接口，避免每次查收盘。"""
    account = getattr(engine, "account", None)
    cash = float(getattr(account, "cash", 0.0) or 0.0) if account is not None else 0.0
    initial = (
        float(getattr(account, "initial_cash", 0.0) or 0.0)
        if account is not None
        else 0.0
    )
    open_count = 0
    if account is not None and callable(getattr(account, "open_position_count", None)):
        open_count = int(account.open_position_count() or 0)
    allocation = getattr(engine, "allocation", None)
    max_size = 0
    if allocation is not None:
        max_size = int(getattr(allocation, "max_portfolio_size", 0) or 0)
    current_date = str(getattr(engine, "current_date", "") or "")
    timeline = getattr(engine, "timeline", None)
    start_date = ""
    end_date = ""
    asof = None
    if timeline is not None:
        start_date = str(getattr(timeline, "start_date", "") or "")
        end_date = str(getattr(timeline, "end_date", "") or "")
        if callable(getattr(timeline, "asof_stats", None)):
            asof = _stats_dict(timeline.asof_stats(current_date))
    draft = _draft_lines(engine)
    phase = str(getattr(engine, "phase", "") or "")
    completed = bool(getattr(engine, "is_completed", False))
    return {
        "dm_id": str(getattr(engine, "dm_id", "") or ""),
        "version_id": str(getattr(engine, "version_id", "") or ""),
        "strategy_key": str(getattr(engine, "strategy_key", "") or ""),
        "status": str(getattr(engine, "status", "") or ""),
        "phase": phase,
        "completed": completed,
        "current_date": current_date,
        "start_date": start_date,
        "end_date": end_date,
        "cash": cash,
        "initial_cash": initial,
        "open_position_count": open_count,
        "max_portfolio_size": max_size,
        "asof_stats": asof,
        "opportunities": [
            _opportunity_dict(opp, engine) for opp in (engine.opportunities() or [])
        ],
        "draft": draft,
        "bill": list(draft) if phase == "confirming" else [],
        "exits": [_exit_dict(item) for item in (exits or ())],
        "report_available": completed,
    }


def holdings_message(engine: Any, rows: Iterable[Any]) -> Dict[str, Any]:
    holdings: List[Dict[str, Any]] = []
    for row in rows or ():
        holdings.append(
            {
                "entity_id": str(getattr(row, "entity_id", "") or ""),
                "name": str(getattr(row, "name", "") or ""),
                "status_tags": _status_tags(getattr(row, "status_tags", None)),
                "shares": int(getattr(row, "shares", 0) or 0),
                "buy_date": str(getattr(row, "buy_date", "") or ""),
                "buy_price": float(getattr(row, "buy_price", 0.0) or 0.0),
                "hold_days": int(getattr(row, "hold_days", 0) or 0),
                "close": getattr(row, "close", None),
                "unrealized": getattr(row, "unrealized", None),
                "goals": [str(item) for item in (getattr(row, "goals", None) or [])],
            }
        )
    return {
        "dm_id": str(getattr(engine, "dm_id", "") or ""),
        "current_date": str(getattr(engine, "current_date", "") or ""),
        "holdings": holdings,
    }


def info_message(payload: Dict[str, Any]) -> Dict[str, Any]:
    """CLI 表 + 与 V2-07c 同形的 candles / indicator_series；NaN 收成 null。"""
    body = dict(payload or {})
    columns = [str(col) for col in (body.get("columns") or [])]
    rows = [_sanitize_row(row) for row in (body.get("rows") or [])]
    candles = [item for row in rows if (item := _candle_from_row(row)) is not None]
    return {
        "entity_id": str(body.get("entity_id") or ""),
        "name": str(body.get("name") or ""),
        "status_tags": _status_tags(body.get("status_tags")),
        "as_of": str(body.get("as_of") or ""),
        "stats": _stats_dict(body.get("stats")),
        "ticker_stats": _stats_dict(body.get("ticker_stats")),
        "columns": columns,
        "rows": rows,
        "candles": candles,
        "indicator_series": _indicator_series_from_rows(columns, rows),
    }


__all__ = [
    "holdings_message",
    "info_message",
    "session_index_row",
    "session_list_message",
    "session_snapshot",
]
