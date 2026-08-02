#!/usr/bin/env python3
"""Generate synthetic market CSVs under ``__performance__/fake_data/``.

Deterministic: fixed seed + stock count + date window.
Does not need a live DB. Output stays inside ``__performance__/``.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

_SCRIPTS = Path(__file__).resolve().parent
_REPO = _SCRIPTS.parents[4]  # .../backtest_engine/__performance__/scripts → repo root
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from common import FAKE_DATA_DIR, ensure_layout, utc_now_iso  # noqa: E402
from config import (  # noqa: E402
    CSV_CALENDAR,
    CSV_KLINES,
    CSV_ST,
    CSV_STOCK_LIST,
    DATASET_ID,
    DATASET_META,
    DEFAULT_END_DATE,
    DEFAULT_KLINE_TERM,
    DEFAULT_SEED,
    DEFAULT_START_DATE,
    DEFAULT_STOCK_COUNT,
    UNIVERSE_TXT,
)
from progress import Progress, step  # noqa: E402


def _yyyymmdd(d: date) -> str:
    return d.strftime("%Y%m%d")


def _parse_yyyymmdd(s: str) -> date:
    return datetime.strptime(s, "%Y%m%d").date()


def _daterange(start: date, end: date) -> Iterable[date]:
    cur = start
    while cur <= end:
        yield cur
        cur += timedelta(days=1)


def build_calendar(start: str, end: str) -> List[dict]:
    """Weekend closed; weekdays open (synthetic, stable)."""
    rows: List[dict] = []
    for d in _daterange(_parse_yyyymmdd(start), _parse_yyyymmdd(end)):
        is_open = 0 if d.weekday() >= 5 else 1
        rows.append({"market": "SSE", "cal_date": _yyyymmdd(d), "is_open": is_open})
    return rows


def build_universe(n: int, *, seed: int) -> List[str]:
    rng = random.Random(seed)
    # Stable fake codes: 600000.SH .. then shuffle with seed for variety
    base = [f"{600000 + i:06d}.SH" for i in range(n)]
    rng.shuffle(base)
    return base


def build_stock_list(ids: Sequence[str], *, list_date: str) -> List[dict]:
    now = utc_now_iso().replace("T", " ").replace("Z", "")
    rows = []
    for i, sid in enumerate(ids):
        rows.append(
            {
                "id": sid,
                "name": f"FAKE{i:04d}",
                "list_status": "L",
                "list_date": list_date,
                "delist_date": "",
                "last_update": now,
            }
        )
    return rows


_KLINE_FIELDS = [
    "id",
    "date",
    "term",
    "open",
    "close",
    "high",
    "low",
    "price_change_delta",
    "price_change_rate_delta",
    "pre_close",
    "volume",
    "amount",
]


def write_daily_klines(
    path: Path,
    ids: Sequence[str],
    open_dates: Sequence[str],
    *,
    seed: int,
) -> int:
    """Stream-generate klines to CSV (avoids holding millions of rows in RAM)."""
    rng = random.Random(seed + 17)
    path.parent.mkdir(parents=True, exist_ok=True)
    expected = len(ids) * len(open_dates)
    step(
        "data_gen",
        f"writing klines → {path.name} "
        f"({len(ids)} stocks × {len(open_dates)} days ≈ {expected:,} rows)",
    )
    prog = Progress("data_gen/klines", len(ids), unit="stocks")
    n_rows = 0
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=_KLINE_FIELDS)
        w.writeheader()
        for sid in ids:
            price = 10.0 + (rng.random() * 40.0)
            for dt in open_dates:
                pre = price
                ret = rng.uniform(-0.03, 0.03)
                close = max(0.5, pre * (1.0 + ret))
                high = max(pre, close) * (1.0 + rng.uniform(0.0, 0.01))
                low = min(pre, close) * (1.0 - rng.uniform(0.0, 0.01))
                open_p = pre * (1.0 + rng.uniform(-0.005, 0.005))
                vol = int(rng.uniform(1e5, 5e6))
                amount = float(vol) * close
                w.writerow(
                    {
                        "id": sid,
                        "date": dt,
                        "term": DEFAULT_KLINE_TERM,
                        "open": round(open_p, 4),
                        "close": round(close, 4),
                        "high": round(high, 4),
                        "low": round(low, 4),
                        "price_change_delta": round(close - pre, 4),
                        "price_change_rate_delta": round(
                            (close / pre - 1.0) * 100.0, 6
                        ),
                        "pre_close": round(pre, 4),
                        "volume": vol,
                        "amount": round(amount, 2),
                    }
                )
                n_rows += 1
                price = close
            prog.update(1)
    prog.finish(extra=f"rows={n_rows:,}")
    return n_rows


def _write_csv(path: Path, rows: Sequence[dict], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(fieldnames))
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fieldnames})


def generate(
    *,
    stock_count: int,
    start_date: str,
    end_date: str,
    seed: int,
) -> Tuple[Path, dict]:
    ensure_layout()
    step(
        "data_gen",
        f"start stocks={stock_count} window={start_date}..{end_date} seed={seed}",
    )
    calendar = build_calendar(start_date, end_date)
    open_dates = [r["cal_date"] for r in calendar if int(r["is_open"]) == 1]
    ids = build_universe(stock_count, seed=seed)
    stock_list = build_stock_list(ids, list_date=start_date)
    step(
        "data_gen",
        f"calendar days={len(calendar)} open_days={len(open_dates)}",
    )

    _write_csv(
        FAKE_DATA_DIR / CSV_STOCK_LIST,
        stock_list,
        ["id", "name", "list_status", "list_date", "delist_date", "last_update"],
    )
    kline_rows = write_daily_klines(
        FAKE_DATA_DIR / CSV_KLINES,
        ids,
        open_dates,
        seed=seed,
    )
    _write_csv(
        FAKE_DATA_DIR / CSV_CALENDAR,
        calendar,
        ["market", "cal_date", "is_open"],
    )
    # empty ST header-only (schema present, zero rows)
    _write_csv(
        FAKE_DATA_DIR / CSV_ST,
        [],
        [
            "stock_id",
            "st_level",
            "start_date",
            "end_date",
            "name_snapshot",
            "change_reason",
        ],
    )
    (FAKE_DATA_DIR / UNIVERSE_TXT).write_text(
        "\n".join(ids) + "\n", encoding="utf-8"
    )

    meta = {
        "dataset_id": DATASET_ID,
        "seed": seed,
        "stock_count": stock_count,
        "start_date": start_date,
        "end_date": end_date,
        "open_days": len(open_dates),
        "kline_rows": kline_rows,
        "term": DEFAULT_KLINE_TERM,
        "generated_at": utc_now_iso(),
        "files": [
            CSV_STOCK_LIST,
            CSV_KLINES,
            CSV_CALENDAR,
            CSV_ST,
            UNIVERSE_TXT,
        ],
    }
    (FAKE_DATA_DIR / DATASET_META).write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    step("data_gen", f"done → {FAKE_DATA_DIR}")
    return FAKE_DATA_DIR, meta


def main(argv: List[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Generate BE performance fake CSVs")
    p.add_argument("--stocks", type=int, default=DEFAULT_STOCK_COUNT)
    p.add_argument("--start-date", default=DEFAULT_START_DATE)
    p.add_argument("--end-date", default=DEFAULT_END_DATE)
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = p.parse_args(argv)

    if args.stocks <= 0:
        raise SystemExit("--stocks must be > 0")
    if args.start_date > args.end_date:
        raise SystemExit("date window invalid")

    out, meta = generate(
        stock_count=args.stocks,
        start_date=args.start_date,
        end_date=args.end_date,
        seed=args.seed,
    )
    print(f"wrote dataset under {out}")
    print(
        f"  stocks={meta['stock_count']} open_days={meta['open_days']} "
        f"klines={meta['kline_rows']} seed={meta['seed']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
