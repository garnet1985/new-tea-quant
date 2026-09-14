"""决策者会话 → FED DTO（页面字段在此命名，不进 Strategy facade）。"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence


def _stats_dict(raw: Any) -> Optional[Dict[str, Any]]:
    if raw is None:
        return None
    if isinstance(raw, dict):
        return {
            "sample_size": int(raw.get("sample_size") or 0),
            "wins": int(raw.get("wins") or 0),
            "win_rate": raw.get("win_rate"),
            "avg_roi": raw.get("avg_roi"),
        }
    to_dict = getattr(raw, "to_dict", None)
    if callable(to_dict):
        return _stats_dict(to_dict())
    return {
        "sample_size": int(getattr(raw, "sample_size", 0) or 0),
        "wins": int(getattr(raw, "wins", 0) or 0),
        "win_rate": getattr(raw, "win_rate", None),
        "avg_roi": getattr(raw, "avg_roi", None),
    }


def _opportunity_dict(opp: Any) -> Dict[str, Any]:
    ticker = getattr(opp, "ticker_stats", None)
    return {
        "local_id": int(getattr(opp, "local_id", 0) or 0),
        "entity_id": str(getattr(opp, "entity_id", "") or ""),
        "name": str(getattr(opp, "name", "") or ""),
        "entry_price": float(getattr(opp, "entry_price_raw", 0.0) or 0.0),
        "stats": _stats_dict(ticker),
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
    asof = None
    if timeline is not None and callable(getattr(timeline, "asof_stats", None)):
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
        "cash": cash,
        "initial_cash": initial,
        "open_position_count": open_count,
        "max_portfolio_size": max_size,
        "asof_stats": asof,
        "opportunities": [
            _opportunity_dict(opp) for opp in (engine.opportunities() or [])
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
    body = dict(payload or {})
    return {
        "entity_id": str(body.get("entity_id") or ""),
        "name": str(body.get("name") or ""),
        "as_of": str(body.get("as_of") or ""),
        "stats": _stats_dict(body.get("stats")),
        "ticker_stats": _stats_dict(body.get("ticker_stats")),
        "columns": list(body.get("columns") or []),
        "rows": list(body.get("rows") or []),
    }


__all__ = [
    "holdings_message",
    "info_message",
    "session_index_row",
    "session_list_message",
    "session_snapshot",
]
