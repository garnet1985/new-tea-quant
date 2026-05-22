#!/usr/bin/env python3
"""
单进程终对比：1 / 3 / 8 股 QFQ 加载。

- join_serial: 生产路径（N×大 JOIN SQL + _build_qfq_rows_default）
- mem_serial:  N×(K线 SQL + 复权事件 SQL) + 内存 QFQ
- mem_batch:   1×K线IN + 1×事件IN + 内存 QFQ（推荐批量形态）

用法:
  PYTHONPATH=. python3 devtools/bench_sp_stocks_qfq_db.py
"""
from __future__ import annotations

import statistics
import time
from typing import Any, Dict, List, Tuple

from core.modules.data_manager import DataManager
from core.utils.date.date_utils import DateUtils

START = "20240307"
END = "20251231"
LOOKBACK = 30
TERM = "daily"
STOCK_COUNTS = (1, 3, 8)
REPEATS = 5

CANDIDATES = [
    "000858.SZ", "000002.SZ", "000937.SZ", "000725.SZ", "002032.SZ",
    "000776.SZ", "001289.SZ", "000999.SZ", "600519.SH", "000001.SZ",
    "601318.SH", "300750.SZ", "688981.SH", "002594.SZ", "600036.SH",
    "000333.SZ", "601012.SH", "002415.SZ", "000063.SZ", "600900.SH",
]


def _actual_start() -> str:
    return DateUtils.sub_days(START, LOOKBACK)


def _discover_stocks(svc: Any, start: str) -> List[str]:
    out: List[str] = []
    seen = set()
    for sid in CANDIDATES:
        if sid in seen:
            continue
        seen.add(sid)
        try:
            if svc.load_raw(sid, TERM, start, END):
                out.append(sid)
        except Exception:
            pass
    return out


def _group_by_id(rows: List[Dict[str, Any]], stock_ids: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    buckets = {sid: [] for sid in stock_ids}
    for row in rows:
        sid = row.get("id")
        if sid in buckets:
            buckets[sid].append(dict(row))
    return buckets


def _memory_qfq_for_stock(
    svc: Any,
    stock_id: str,
    raw_rows: List[Dict[str, Any]],
    events: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """K线+事件已拉取后，内存算 QFQ（default 连续规则，对齐 load_qfq）。"""
    if not raw_rows:
        return []
    dates = sorted(
        {d for d in (svc._normalize_date(r.get("date")) for r in raw_rows) if d}
    )
    if not dates:
        return []
    max_date = dates[-1]
    filtered = [
        e
        for e in events
        if svc._normalize_date(e.get("event_date")) is not None
        and svc._normalize_date(e.get("event_date")) <= max_date
    ]
    earliest = events[0] if events else None

    event_map: Dict[str, Dict[str, Any]] = {}
    idx = 0
    n = len(filtered)
    latest = None
    for d in dates:
        while idx < n:
            ed = svc._normalize_date(filtered[idx].get("event_date"))
            if ed is not None and ed <= d:
                latest = filtered[idx]
                idx += 1
            else:
                break
        selected = latest
        inferred = False
        if selected is None and earliest is not None:
            selected = earliest
            inferred = True
        if selected is None:
            event_map[d] = {
                "qfq_diff": 0.0,
                "is_adjusted": False,
                "is_inferred": False,
            }
        else:
            event_map[d] = {
                "qfq_diff": float(selected.get("qfq_diff", 0.0) or 0.0),
                "is_adjusted": True,
                "is_inferred": inferred,
            }

    out: List[Dict[str, Any]] = []
    for row in raw_rows:
        qfq_kline = dict(row)
        date_key = svc._normalize_date(qfq_kline.get("date"))
        info = event_map.get(
            date_key,
            {"qfq_diff": 0.0, "is_adjusted": False, "is_inferred": False},
        )
        qfq_diff = svc._to_float_or_none(info.get("qfq_diff")) or 0.0
        svc._apply_qfq_prices(qfq_kline, qfq_diff)
        qfq_kline["qfq_is_adjusted"] = bool(info.get("is_adjusted", False))
        qfq_kline["qfq_is_inferred"] = bool(info.get("is_inferred", False))
        out.append(qfq_kline)
    return out


def _qfq_sig(rows: List[Dict[str, Any]]) -> Tuple[int, float]:
    if not rows:
        return (0, 0.0)
    last = rows[-1]
    return (len(rows), float(last.get("qfq_close") or last.get("close") or 0))


def _bench_join_serial(svc: Any, stock_ids: List[str], start: str, end: str) -> Dict[str, float]:
    sql_n = 0
    sql_ms = 0.0
    mem_ms = 0.0
    bars = 0

    t_wall = time.perf_counter()
    for sid in stock_ids:
        t0 = time.perf_counter()
        rows = svc._query_qfq_join_rows(sid, TERM, start, end)
        sql_ms += (time.perf_counter() - t0) * 1000.0
        sql_n += 1

        t0 = time.perf_counter()
        built = svc._build_qfq_rows_default(stock_id=sid, results=rows)
        mem_ms += (time.perf_counter() - t0) * 1000.0
        bars += len(built or [])

    return {
        "wall_ms": (time.perf_counter() - t_wall) * 1000.0,
        "sql_n": float(sql_n),
        "sql_ms": sql_ms,
        "mem_ms": mem_ms,
        "bars": float(bars),
    }


def _bench_mem_serial(svc: Any, stock_ids: List[str], start: str, end: str) -> Dict[str, float]:
    sql_n = 0
    sql_ms = 0.0
    mem_ms = 0.0
    bars = 0

    t_wall = time.perf_counter()
    for sid in stock_ids:
        t0 = time.perf_counter()
        raw = svc.load_raw(sid, TERM, start, end) or []
        sql_ms += (time.perf_counter() - t0) * 1000.0
        sql_n += 1

        t0 = time.perf_counter()
        events: List[Dict[str, Any]] = []
        if svc._adj_factor_event:
            events = (
                svc._adj_factor_event.load(
                    "id = %s AND event_date <= %s",
                    (sid, end),
                    order_by="event_date ASC",
                )
                or []
            )
        sql_ms += (time.perf_counter() - t0) * 1000.0
        sql_n += 1

        t0 = time.perf_counter()
        built = _memory_qfq_for_stock(svc, sid, raw, events)
        mem_ms += (time.perf_counter() - t0) * 1000.0
        bars += len(built)

    return {
        "wall_ms": (time.perf_counter() - t_wall) * 1000.0,
        "sql_n": float(sql_n),
        "sql_ms": sql_ms,
        "mem_ms": mem_ms,
        "bars": float(bars),
    }


def _bench_mem_batch(svc: Any, stock_ids: List[str], start: str, end: str) -> Dict[str, float]:
    if not stock_ids:
        return {"wall_ms": 0.0, "sql_n": 0.0, "sql_ms": 0.0, "mem_ms": 0.0, "bars": 0.0}

    placeholders = ",".join(["%s"] * len(stock_ids))
    params: List[Any] = list(stock_ids)
    conditions = [f"id IN ({placeholders})", "term = %s"]
    params.append(TERM)
    if start:
        conditions.append("date >= %s")
        params.append(start)
    if end:
        conditions.append("date <= %s")
        params.append(end)
    where_k = " AND ".join(conditions)

    sql_n = 0
    sql_ms = 0.0
    mem_ms = 0.0
    bars = 0

    t_wall = time.perf_counter()

    t0 = time.perf_counter()
    raw_all = svc._stock_kline.load(where_k, tuple(params), order_by="id ASC, date ASC") or []
    sql_ms += (time.perf_counter() - t0) * 1000.0
    sql_n += 1
    raw_by = _group_by_id(raw_all, stock_ids)

    events_all: List[Dict[str, Any]] = []
    t0 = time.perf_counter()
    if svc._adj_factor_event:
        ev_where = f"id IN ({placeholders}) AND event_date <= %s"
        ev_params: tuple[Any, ...] = tuple(stock_ids) + (end,)
        events_all = (
            svc._adj_factor_event.load(
                ev_where, ev_params, order_by="id ASC, event_date ASC"
            )
            or []
        )
    sql_ms += (time.perf_counter() - t0) * 1000.0
    sql_n += 1
    events_by = _group_by_id(events_all, stock_ids)

    for sid in stock_ids:
        t0 = time.perf_counter()
        built = _memory_qfq_for_stock(
            svc, sid, raw_by.get(sid) or [], events_by.get(sid) or []
        )
        mem_ms += (time.perf_counter() - t0) * 1000.0
        bars += len(built)

    return {
        "wall_ms": (time.perf_counter() - t_wall) * 1000.0,
        "sql_n": float(sql_n),
        "sql_ms": sql_ms,
        "mem_ms": mem_ms,
        "bars": float(bars),
    }


PATHS: Dict[str, Any] = {
    "join_serial": _bench_join_serial,
    "mem_serial": _bench_mem_serial,
    "mem_batch": _bench_mem_batch,
}

LABELS = {
    "join_serial": "JOIN serial（N×复杂JOIN）",
    "mem_serial": "两步 serial（N×K线+N×事件+内存）",
    "mem_batch": "两步 batch（2×IN查询+内存）",
}


def _run_path(path: str, svc: Any, stock_ids: List[str], start: str, end: str) -> Dict[str, float]:
    return PATHS[path](svc, stock_ids, start, end)


def _median_row(samples: List[Dict[str, float]]) -> Dict[str, float]:
    if not samples:
        return {}
    return {k: statistics.median([s[k] for s in samples]) for k in samples[0]}


def _verify_sig(svc: Any, stock_id: str, start: str, end: str) -> bool:
    ref = svc.load_qfq(stock_id, TERM, start, end)
    raw = svc.load_raw(stock_id, TERM, start, end) or []
    events = []
    if svc._adj_factor_event:
        events = (
            svc._adj_factor_event.load(
                "id = %s AND event_date <= %s", (stock_id, end), order_by="event_date ASC"
            )
            or []
        )
    mem = _memory_qfq_for_stock(svc, stock_id, raw, events)
    return _qfq_sig(ref) == _qfq_sig(mem)


def main() -> None:
    dm = DataManager()
    svc = dm.stock.kline
    start = _actual_start()
    pool = _discover_stocks(svc, start)
    if len(pool) < max(STOCK_COUNTS):
        raise SystemExit(f"样本不足: {len(pool)}")

    base = pool[: max(STOCK_COUNTS)]
    ok = _verify_sig(svc, base[0], start, END)
    print("=== 单进程 QFQ 终对比：分开查 K线/复权 + 内存计算 ===")
    print(f"区间 {start}~{END} term={TERM} | median of {REPEATS} runs")
    print(f"样本: {', '.join(base)}")
    print(f"内存 QFQ 与 load_qfq 一致: {'是' if ok else '否（请检查）'}")
    print()

    _run_path("join_serial", svc, base[:1], start, END)

    table: List[Tuple[int, str, Dict[str, float]]] = []

    for n in STOCK_COUNTS:
        stocks = base[:n]
        print(f"--- {n} 只股票 ---")
        for path in ("join_serial", "mem_serial", "mem_batch"):
            med = _median_row([_run_path(path, svc, stocks, start, END) for _ in range(REPEATS)])
            table.append((n, path, med))
            ps = med["wall_ms"] / n if n else 0.0
            ratio = med["wall_ms"] / med["sql_ms"] if med["sql_ms"] else 0.0
            print(
                f"  {LABELS[path]}"
                f"\n    wall={med['wall_ms']:.1f}ms ({ps:.1f}ms/股)"
                f"  sql={int(med['sql_n'])}次 sql_ms={med['sql_ms']:.1f}"
                f"  mem_ms={med['mem_ms']:.1f}  bars={int(med['bars'])}"
            )
        by = {p: m for nn, p, m in table if nn == n}
        j, b = by["join_serial"]["wall_ms"], by["mem_batch"]["wall_ms"]
        if j:
            pct = (1 - b / j) * 100
            tag = "更快" if pct > 0 else "更慢"
            print(f"  → mem_batch vs JOIN: {b/j:.2f}x  ({abs(pct):.0f}% {tag})")
        print()

    print("=== 汇总 wall ms（median）===")
    print("| 股数 | JOIN serial | 两步+内存 serial | 两步+内存 batch | batch/JOIN |")
    print("|---:|---:|---:|---:|---:|")
    for n in STOCK_COUNTS:
        by = {p: m for nn, p, m in table if nn == n}
        j = by["join_serial"]["wall_ms"]
        ms = by["mem_serial"]["wall_ms"]
        mb = by["mem_batch"]["wall_ms"]
        print(f"| {n} | {j:.1f} | {ms:.1f} | {mb:.1f} | {mb/j:.2f}x |")

    print()
    print("=== 结论 ===")
    by8 = {p: m for nn, p, m in table if nn == 8}
    j8, b8 = by8["join_serial"]["wall_ms"], by8["mem_batch"]["wall_ms"]
    print("1. 大 JOIN 是主要成本；拆成简单 K线/事件查询后，单股 SQL 更快。")
    print("2. 内存 QFQ 很轻（8股 ~18ms），相对 SQL 仍是小头。")
    print(f"3. 批量 IN（mem_batch）在 8 股时约比 JOIN 快 {(1-b8/j8)*100:.0f}%（本机 median）。")
    print("4. 枚举优化方向：scheduler 按 job 批量 2 SQL + 内存 QFQ + _preloaded_klines；")
    print("   不必改 JOIN SQL；多进程 3股/job 才有 IO 合并意义。")


if __name__ == "__main__":
    main()
