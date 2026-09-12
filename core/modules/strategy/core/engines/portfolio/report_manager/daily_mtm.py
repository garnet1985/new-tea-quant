"""资金层日频盯市：成交 + 开市日 + 持仓窗 hfq 收盘 → 日净值。

计价与现金盈亏同一把尺：
    ROI_d   = (hfq_close_d − entry_hfq) / entry_hfq
    value   = buy_shares × entry_raw × (1 + ROI_d)

``entry_hfq`` 是买入成交后复权价，不是买入日收盘。买入当天含 fill→收盘。
假设红利再投资同一标的（因子口径，不接 dividend 双账户）。

边界: 允许 IO；失败时保留模拟器成本曲线，不改成交。调用方: ReportManager.finalize。
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from core.modules.strategy.core.engines.portfolio.simulator import PortfolioSimResult

logger = logging.getLogger(__name__)

_BATCH_SIZE = 15
_CALENDAR_MARKET = "SSE"

LoadOpenDates = Callable[[str, str], Sequence[str]]
LoadHfqCloses = Callable[[str, str, str], Dict[str, float]]


@dataclass
class _OpenLot:
    entity_id: str
    investment_id: str
    shares: int
    entry_raw: float
    entry_hfq: float


def mark_portfolio_equity(
    sim: PortfolioSimResult,
    *,
    start_date: str = "",
    end_date: str = "",
    market_profile: str = "",
    load_open_dates: Optional[LoadOpenDates] = None,
    load_hfq_closes: Optional[LoadHfqCloses] = None,
    batch_size: int = _BATCH_SIZE,
) -> PortfolioSimResult:
    """用日频盯市曲线替换 ``sim.equity_curve``。日历/K 线失败则原样返回。"""
    _ = market_profile
    if sim is None or getattr(sim, "equity_marked_to_market", False):
        return sim
    try:
        points = build_daily_equity(
            sim,
            start_date=start_date,
            end_date=end_date,
            load_open_dates=load_open_dates or _default_load_open_dates,
            load_hfq_closes=load_hfq_closes or _default_load_hfq_closes,
            batch_size=batch_size,
        )
    except Exception:
        logger.exception("资金层日频盯市失败，保留成本曲线")
        return sim
    if not points:
        logger.warning("资金层日频盯市未产出净值点，保留成本曲线")
        return sim
    sim.equity_curve = points
    sim.equity_marked_to_market = True
    return sim


def build_daily_equity(
    sim: PortfolioSimResult,
    *,
    start_date: str = "",
    end_date: str = "",
    load_open_dates: LoadOpenDates,
    load_hfq_closes: LoadHfqCloses,
    batch_size: int = _BATCH_SIZE,
) -> List[Dict[str, float | int | str]]:
    """成交回放 + 持仓窗 hfq 收盘 → 每个开市日 ``{date, cash, equity, open_positions}``。"""
    account = getattr(sim, "account", None)
    initial = float(getattr(account, "initial_cash", 0.0) or 0.0)
    trades = _sorted_trades(getattr(sim, "trades", None) or [])
    start, end = _period_bounds(trades, start_date, end_date)
    if not start or not end or start > end:
        return []

    open_dates = [
        d
        for d in (_norm_date(x) for x in (load_open_dates(start, end) or []))
        if d and start <= d <= end
    ]
    if not open_dates:
        return []

    windows = _hold_windows(trades, end)
    closes = _load_closes_batched(
        windows,
        load_hfq_closes=load_hfq_closes,
        batch_size=max(1, int(batch_size or _BATCH_SIZE)),
    )
    return _replay_daily(open_dates, trades, initial=initial, closes=closes)


def hfq_close_from_bar(bar: Any) -> Optional[float]:
    """分层 bar 的后复权收盘；缺嵌套 hfq 时用 raw × adj_factor。"""
    if not isinstance(bar, dict):
        return None
    nested = bar.get("hfq")
    if isinstance(nested, dict) and nested.get("close") is not None:
        px = _positive_float(nested.get("close"))
        if px is not None:
            return px
    raw = bar.get("raw") if isinstance(bar.get("raw"), dict) else {}
    raw_close = _positive_float(raw.get("close") if isinstance(raw, dict) else None)
    adj = bar.get("adj_factor")
    if raw_close is None or adj is None or adj == "":
        return None
    try:
        px = float(raw_close) * float(adj)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(px) or px <= 0:
        return None
    return px


def _replay_daily(
    open_dates: Sequence[str],
    trades: Sequence[Any],
    *,
    initial: float,
    closes: Dict[str, Dict[str, float]],
) -> List[Dict[str, float | int | str]]:
    by_date: Dict[str, List[Any]] = {}
    for trade in trades:
        day = _norm_date(getattr(trade, "date", ""))
        if not day:
            continue
        by_date.setdefault(day, []).append(trade)

    cash = float(initial)
    lots: Dict[str, _OpenLot] = {}
    last_hfq: Dict[str, float] = {}
    points: List[Dict[str, float | int | str]] = []

    for day in open_dates:
        for trade in by_date.get(day, []):
            cash, _ = _apply_trade(cash, lots, trade)
        equity = cash
        for lot in lots.values():
            today = (closes.get(lot.entity_id) or {}).get(day)
            if today is not None:
                last_hfq[lot.entity_id] = today
            equity += _mark_value(lot, last_hfq.get(lot.entity_id))
        points.append(
            {
                "date": day,
                "cash": float(cash),
                "equity": float(equity),
                "open_positions": int(len({lot.entity_id for lot in lots.values()})),
            }
        )
    return points


def _apply_trade(
    cash: float,
    lots: Dict[str, _OpenLot],
    trade: Any,
) -> Tuple[float, Dict[str, _OpenLot]]:
    key = _lot_key(
        str(getattr(trade, "entity_id", "") or ""),
        str(getattr(trade, "investment_id", "") or ""),
    )
    if not key.strip("\t"):
        return cash, lots
    is_buy = bool(getattr(trade, "is_buy", lambda: False)())
    is_sell = bool(getattr(trade, "is_sell", lambda: False)())
    shares = int(getattr(trade, "shares", 0) or 0)
    if is_buy:
        cost = getattr(trade, "total_cost", None)
        if cost is None:
            cost = float(getattr(trade, "amount", 0.0) or 0.0) + float(
                getattr(trade, "fees", 0.0) or 0.0
            )
        cash -= float(cost or 0.0)
        entry_raw = float(getattr(trade, "price", 0.0) or 0.0)
        entry_hfq = float(getattr(trade, "entry_price_hfq", 0.0) or 0.0)
        existing = lots.get(key)
        if existing is None:
            lots[key] = _OpenLot(
                entity_id=str(getattr(trade, "entity_id", "") or "").strip(),
                investment_id=str(getattr(trade, "investment_id", "") or "").strip(),
                shares=shares,
                entry_raw=entry_raw,
                entry_hfq=entry_hfq,
            )
        else:
            existing.shares += shares
        return cash, lots
    if is_sell:
        proceeds = getattr(trade, "net_proceeds", None)
        if proceeds is None:
            proceeds = float(getattr(trade, "amount", 0.0) or 0.0) - float(
                getattr(trade, "fees", 0.0) or 0.0
            )
        cash += float(proceeds or 0.0)
        lot = lots.get(key)
        if lot is not None:
            lot.shares = max(0, int(lot.shares) - shares)
            if lot.shares <= 0:
                lots.pop(key, None)
    return cash, lots


def _mark_value(lot: _OpenLot, hfq_close: Optional[float]) -> float:
    shares = int(lot.shares or 0)
    entry_raw = float(lot.entry_raw or 0.0)
    if shares <= 0 or entry_raw <= 0:
        return 0.0
    px = float(hfq_close) if hfq_close is not None else 0.0
    if not math.isfinite(px) or px <= 0:
        return float(shares) * entry_raw
    entry_hfq = float(lot.entry_hfq or 0.0)
    if entry_hfq <= 0:
        lot.entry_hfq = px
        entry_hfq = px
    roi = px / entry_hfq - 1.0
    return float(shares) * entry_raw * (1.0 + roi)


def _hold_windows(
    trades: Sequence[Any],
    end_date: str,
) -> Dict[str, Tuple[str, str]]:
    """每只曾持有股票：首次买入日 → 最后卖出日或 end_date。"""
    first_buy: Dict[str, str] = {}
    last_sell: Dict[str, str] = {}
    still_open: Dict[str, int] = {}
    for trade in trades:
        eid = str(getattr(trade, "entity_id", "") or "").strip()
        day = _norm_date(getattr(trade, "date", ""))
        if not eid or not day:
            continue
        if getattr(trade, "is_buy", lambda: False)():
            first_buy.setdefault(eid, day)
            still_open[eid] = still_open.get(eid, 0) + 1
        elif getattr(trade, "is_sell", lambda: False)():
            last_sell[eid] = day
            still_open[eid] = still_open.get(eid, 0) - 1
    windows: Dict[str, Tuple[str, str]] = {}
    for eid, start in first_buy.items():
        if still_open.get(eid, 0) > 0:
            stop = end_date
        else:
            stop = last_sell.get(eid) or end_date
        if start and stop and start <= stop:
            windows[eid] = (start, stop)
    return windows


def _load_closes_batched(
    windows: Dict[str, Tuple[str, str]],
    *,
    load_hfq_closes: LoadHfqCloses,
    batch_size: int,
) -> Dict[str, Dict[str, float]]:
    out: Dict[str, Dict[str, float]] = {}
    names = list(windows.keys())
    for i in range(0, len(names), batch_size):
        batch = names[i : i + batch_size]
        for eid in batch:
            start, stop = windows[eid]
            try:
                rows = load_hfq_closes(eid, start, stop) or {}
            except Exception:
                logger.warning("盯市拉 K 失败，按缺 bar 处理: entity_id=%s", eid, exc_info=True)
                rows = {}
            mapped: Dict[str, float] = {}
            for raw_day, px in dict(rows).items():
                day = _norm_date(raw_day)
                val = _positive_float(px)
                if day and val is not None:
                    mapped[day] = val
            out[eid] = mapped
    return out


def _sorted_trades(trades: Sequence[Any]) -> List[Any]:
    def _side_rank(trade: Any) -> int:
        if getattr(trade, "is_buy", lambda: False)():
            return 0
        if getattr(trade, "is_sell", lambda: False)():
            return 1
        return 2

    return sorted(
        list(trades),
        key=lambda t: (
            _norm_date(getattr(t, "date", "")),
            _side_rank(t),
            str(getattr(t, "entity_id", "") or ""),
            str(getattr(t, "investment_id", "") or ""),
        ),
    )


def _period_bounds(
    trades: Sequence[Any],
    start_date: str,
    end_date: str,
) -> Tuple[str, str]:
    start = _norm_date(start_date)
    end = _norm_date(end_date)
    trade_days = [_norm_date(getattr(t, "date", "")) for t in trades]
    trade_days = [d for d in trade_days if d]
    if not start and trade_days:
        start = min(trade_days)
    if not end and trade_days:
        end = max(trade_days)
    return start, end


def _lot_key(entity_id: str, investment_id: str) -> str:
    return f"{str(entity_id or '').strip()}\t{str(investment_id or '').strip()}"


def _norm_date(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return text.replace("-", "").replace("/", "")[:8]


def _positive_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(out) or out <= 0:
        return None
    return out


def _default_load_open_dates(start: str, end: str) -> List[str]:
    try:
        from core.modules.data_manager import DataManager

        rows = DataManager().service.calendar.load_open_dates(
            start, end, market=_CALENDAR_MARKET
        )
    except Exception:
        logger.warning("盯市读交易日历失败 %s..%s", start, end, exc_info=True)
        return []
    return [_norm_date(d) for d in (rows or []) if _norm_date(d)]


def _default_load_hfq_closes(entity_id: str, start: str, end: str) -> Dict[str, float]:
    from core.modules.strategy.core.engines.price_factor.helpers.klines_loader import (
        load_stock_klines,
    )

    out: Dict[str, float] = {}
    for bar in load_stock_klines(entity_id, start_date=start, end_date=end) or []:
        day = _norm_date(bar.get("date") if isinstance(bar, dict) else "")
        px = hfq_close_from_bar(bar)
        if day and px is not None:
            out[day] = px
    return out


__all__ = [
    "mark_portfolio_equity",
    "build_daily_equity",
    "hfq_close_from_bar",
]
