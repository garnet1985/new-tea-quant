"""trading_calendar：查询本机 A 股交易日历（sys_data_trade_calendar）。"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List

from core.modules.agent.core.code.conf.conf import TRADING_CALENDAR_RANGE_MAX_DAYS
from core.modules.data_manager import DataManager


def trading_calendar(arguments: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """查开市日 / 最新已完成交易日 / 区间开市列表。

    - 给 ``start``+``end``：返回区间内开市日列表。
    - 否则按 ``date``（默认今天）返回是否开市、上一/下一开市日、最新已完成交易日。
    """
    args = arguments if isinstance(arguments, dict) else {}
    extra = set(args) - {"date", "start", "end", "market"}
    if extra:
        return {"ok": False, "error": f"不支持的参数: {', '.join(sorted(extra))}"}

    market = str(args.get("market") or "SSE").strip() or "SSE"
    start = _norm_ymd(args.get("start"))
    end = _norm_ymd(args.get("end"))
    if (start and not end) or (end and not start):
        return {"ok": False, "error": "start 与 end 须同时提供（YYYYMMDD）"}
    if start and end:
        return _range(start, end, market=market)

    date = _norm_ymd(args.get("date"))
    if args.get("date") is not None and not date:
        return {"ok": False, "error": "date 须为 YYYYMMDD"}
    if not date:
        date = _today()
    return _lookup(date, market=market)


def _lookup(date: str, *, market: str) -> Dict[str, Any]:
    try:
        cal = DataManager().calendar
    except Exception as exc:
        return {"ok": False, "error": f"无法打开日历服务: {exc}"}

    try:
        is_open = date in set(cal.load_open_dates(date, date, market=market) or [])
    except Exception as exc:
        return {"ok": False, "error": f"无法判断开市: {exc}"}

    next_open = ""
    try:
        next_open = str(cal.get_next_trading_date(date, market=market) or "").strip()
    except Exception:
        next_open = ""

    prev_open = _prev_open(cal, date, market=market)

    latest_completed = ""
    try:
        latest_completed = str(
            cal.get_latest_completed_trading_date(as_of_date=date) or ""
        ).strip()
    except Exception:
        latest_completed = ""

    return {
        "ok": True,
        "date": date,
        "is_open": bool(is_open),
        "prev_open": prev_open or None,
        "next_open": next_open or None,
        "latest_completed": latest_completed or None,
        "market": market,
        "note": (
            "基于本机 sys_data_trade_calendar（默认 market=SSE）。"
            "latest_completed 是计算侧最新已完成交易日，不是实时盘口。"
        ),
    }


def _range(start: str, end: str, *, market: str) -> Dict[str, Any]:
    if start > end:
        return {"ok": False, "error": "start 不能晚于 end"}
    try:
        d0 = datetime.strptime(start, "%Y%m%d")
        d1 = datetime.strptime(end, "%Y%m%d")
    except ValueError:
        return {"ok": False, "error": "start/end 须为合法 YYYYMMDD"}
    span = (d1 - d0).days + 1
    if span > TRADING_CALENDAR_RANGE_MAX_DAYS:
        return {
            "ok": False,
            "error": f"区间最长 {TRADING_CALENDAR_RANGE_MAX_DAYS} 天，当前 {span}",
        }
    try:
        cal = DataManager().calendar
        opens: List[str] = list(cal.load_open_dates(start, end, market=market) or [])
    except Exception as exc:
        return {"ok": False, "error": f"无法读取开市日: {exc}"}
    return {
        "ok": True,
        "start": start,
        "end": end,
        "market": market,
        "open_dates": opens,
        "count": len(opens),
        "note": "开市日升序 YYYYMMDD；休市日不在列表中。",
    }


def _prev_open(cal: Any, date: str, *, market: str) -> str:
    try:
        anchor = datetime.strptime(date, "%Y%m%d")
    except ValueError:
        return ""
    start = (anchor - timedelta(days=40)).strftime("%Y%m%d")
    end = (anchor - timedelta(days=1)).strftime("%Y%m%d")
    if end < start:
        return ""
    try:
        opens = list(cal.load_open_dates(start, end, market=market) or [])
    except Exception:
        return ""
    return str(opens[-1]).strip() if opens else ""


def _norm_ymd(value: Any) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        return ""
    raw = value.strip().replace("-", "").replace("/", "")
    if len(raw) != 8 or not raw.isdigit():
        return ""
    try:
        datetime.strptime(raw, "%Y%m%d")
    except ValueError:
        return ""
    return raw


def _today() -> str:
    try:
        from core.infra.utils import Utils

        return str(Utils.date.today() or "").strip()
    except Exception:
        return datetime.now().strftime("%Y%m%d")
