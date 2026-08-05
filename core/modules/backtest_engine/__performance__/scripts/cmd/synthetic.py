"""Synthetic market rows for BE perf seeding (no CSV).

Deterministic, minimal realism: continuous IDs + fixed-pattern OHLC.
Enough for null-strategy throughput; not a market simulator.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Dict, Iterable, Iterator, List, Sequence


def parse_yyyymmdd(s: str) -> date:
    return datetime.strptime(str(s), "%Y%m%d").date()


def yyyymmdd(d: date) -> str:
    return d.strftime("%Y%m%d")


def daterange(start: date, end: date) -> Iterable[date]:
    cur = start
    while cur <= end:
        yield cur
        cur += timedelta(days=1)


def stock_ids(count: int) -> List[str]:
    """Continuous fake IDs: ``000000`` .. ``{count-1:06d}``."""
    n = max(0, int(count))
    return [f"{i:06d}" for i in range(n)]


def build_calendar(start: str, end: str) -> List[Dict[str, object]]:
    """Weekends closed; weekdays open."""
    rows: List[Dict[str, object]] = []
    for d in daterange(parse_yyyymmdd(start), parse_yyyymmdd(end)):
        rows.append(
            {
                "market": "SSE",
                "cal_date": yyyymmdd(d),
                "is_open": 0 if d.weekday() >= 5 else 1,
            }
        )
    return rows


def open_dates(start: str, end: str) -> List[str]:
    return [r["cal_date"] for r in build_calendar(start, end) if int(r["is_open"]) == 1]


def build_stock_list(ids: Sequence[str], *, list_date: str, now: str) -> List[Dict[str, str]]:
    stamp = now.replace("T", " ").replace("Z", "")
    return [
        {
            "id": sid,
            "name": f"FAKE{sid}",
            "list_status": "L",
            "list_date": list_date,
            "delist_date": "",
            "last_update": stamp,
        }
        for sid in ids
    ]


def _ohlc_for_day(day_index: int) -> Dict[str, float]:
    """Fixed-pattern prices (no RNG)."""
    close = 10.0 + (day_index % 100) * 0.01
    open_p = close
    high = round(close * 1.01, 4)
    low = round(close * 0.99, 4)
    pre = close if day_index == 0 else 10.0 + ((day_index - 1) % 100) * 0.01
    return {
        "open": round(open_p, 4),
        "close": round(close, 4),
        "high": high,
        "low": low,
        "pre_close": round(pre, 4),
        "price_change_delta": round(close - pre, 4),
        "price_change_rate_delta": round((close / pre - 1.0) * 100.0, 6) if pre else 0.0,
    }


def iter_kline_batches(
    ids: Sequence[str],
    dates: Sequence[str],
    *,
    term: str,
    batch_size: int = 20_000,
) -> Iterator[List[Dict[str, object]]]:
    """Yield kline row batches for direct DB insert."""
    buf: List[Dict[str, object]] = []
    for sid in ids:
        for day_i, dt in enumerate(dates):
            px = _ohlc_for_day(day_i)
            vol = 100_000 + (day_i % 50) * 1000
            buf.append(
                {
                    "id": sid,
                    "date": dt,
                    "term": term,
                    "open": px["open"],
                    "close": px["close"],
                    "high": px["high"],
                    "low": px["low"],
                    "price_change_delta": px["price_change_delta"],
                    "price_change_rate_delta": px["price_change_rate_delta"],
                    "pre_close": px["pre_close"],
                    "volume": vol,
                    "amount": round(float(vol) * float(px["close"]), 2),
                }
            )
            if len(buf) >= batch_size:
                yield buf
                buf = []
    if buf:
        yield buf
