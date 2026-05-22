#!/usr/bin/env python3
"""
对比 QFQ 加载：大 JOIN（load_qfq） vs 两次查询 + 内存复权。

用法（仓库根目录）:
  python3 devtools/bench_qfq_join_vs_two_step.py
"""
from __future__ import annotations

import statistics
import time
from typing import Any, Dict, List, Tuple

from core.modules.data_manager import DataManager
from core.utils.date.date_utils import DateUtils

# 与 example 枚举一致
START = "20240307"
END = "20251231"
LOOKBACK = 30
TERM = "daily"

SAMPLE_STOCKS = [
    "000858.SZ",
    "000002.SZ",
    "000937.SZ",
    "600000.SH",
    "000725.SZ",
    "002032.SZ",
    "000776.SZ",
    "001289.SZ",
    "000999.SZ",
    "600519.SH",
    "000001.SZ",
    "601318.SH",
    "300750.SZ",
    "688981.SH",
    "002594.SZ",
    "000858.SZ",
    "600036.SH",
    "000333.SZ",
    "601012.SH",
    "002415.SZ",
]


def _actual_start() -> str:
    return DateUtils.sub_days(START, LOOKBACK)


def _summarize(samples_ms: List[float]) -> Dict[str, float]:
    if not samples_ms:
        return {"n": 0, "median": 0.0, "mean": 0.0, "p95": 0.0, "sum": 0.0}
    s = sorted(samples_ms)
    return {
        "n": len(s),
        "median": statistics.median(s),
        "mean": statistics.mean(s),
        "p95": s[int(0.95 * len(s)) - 1],
        "sum": sum(s),
    }


def _qfq_signature(rows: List[Dict[str, Any]]) -> Tuple[int, float, float]:
    if not rows:
        return (0, 0.0, 0.0)
    last = rows[-1]
    return (
        len(rows),
        float(last.get("close") or 0),
        float(last.get("qfq_close") or last.get("close") or 0),
    )


def _memory_build_qfq(
    svc: Any,
    stock_id: str,
    raw: List[Dict[str, Any]],
    event_map: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """两次 SQL 之后纯 Python 复权（不再打 DB）。"""
    out: List[Dict[str, Any]] = []
    for row in raw:
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


def _event_map_from_loaded_events(
    svc: Any,
    stock_id: str,
    raw: List[Dict[str, Any]],
    events: List[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """用已拉取的 events 行在内存构造 date->effective map（对齐 default 规则）。"""
    dates = sorted(
        {d for d in (svc._normalize_date(r.get("date")) for r in raw) if d}
    )
    if not dates:
        return {}
    max_date = dates[-1]
    filtered = [
        e
        for e in events
        if svc._normalize_date(e.get("event_date")) is not None
        and svc._normalize_date(e.get("event_date")) <= max_date
    ]
    earliest = events[0] if events else None

    out: Dict[str, Dict[str, Any]] = {}
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
            out[d] = {
                "event": None,
                "qfq_diff": 0.0,
                "is_adjusted": False,
                "is_inferred": False,
            }
        else:
            qfq_diff = float(selected.get("qfq_diff", 0.0) or 0.0)
            out[d] = {
                "event": selected,
                "qfq_diff": qfq_diff,
                "is_adjusted": True,
                "is_inferred": inferred,
            }
    return out


def bench_one_stock(svc: Any, stock_id: str, start: str, end: str) -> Dict[str, Any]:
    timings: Dict[str, float] = {}
    join_rows: List[Dict[str, Any]] = []
    raw_rows: List[Dict[str, Any]] = []
    events_rows: List[Dict[str, Any]] = []

    # --- JOIN: 查询 ---
    t0 = time.perf_counter()
    join_rows = svc._query_qfq_join_rows(stock_id, TERM, start, end)
    timings["join_sql"] = (time.perf_counter() - t0) * 1000

    # --- JOIN: Python 构建 ---
    t0 = time.perf_counter()
    join_built = svc._build_qfq_rows_default(stock_id=stock_id, results=join_rows)
    timings["join_build"] = (time.perf_counter() - t0) * 1000
    timings["join_total"] = timings["join_sql"] + timings["join_build"]

    # --- JOIN: 端到端 load_qfq ---
    t0 = time.perf_counter()
    join_e2e = svc.load_qfq(stock_id, TERM, start, end)
    timings["join_e2e"] = (time.perf_counter() - t0) * 1000

    # --- 两步: raw ---
    t0 = time.perf_counter()
    raw_rows = svc.load_raw(stock_id, TERM, start, end)
    timings["raw_sql"] = (time.perf_counter() - t0) * 1000

    # --- 两步: 复权事件（与 load_effective_events_for_dates 同条件的单次拉取）---
    t0 = time.perf_counter()
    if svc._adj_factor_event:
        events_rows = svc._adj_factor_event.load(
            "id = %s AND event_date <= %s",
            (stock_id, end),
            order_by="event_date ASC",
        ) or []
    timings["events_sql"] = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    event_map = _event_map_from_loaded_events(svc, stock_id, raw_rows, events_rows)
    timings["two_map_mem"] = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    two_build_via_api = svc._build_qfq_rows_default(
        stock_id=stock_id, results=[dict(r) for r in raw_rows]
    )
    timings["two_build_api"] = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    two_memory = _memory_build_qfq(svc, stock_id, raw_rows, event_map)
    timings["two_build_mem"] = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    two_e2e = svc._load_qfq_fallback(stock_id, TERM, start, end, is_strict=False)
    timings["two_e2e_fallback"] = (time.perf_counter() - t0) * 1000

    timings["two_sql_sum"] = timings["raw_sql"] + timings["events_sql"]
    timings["two_total_explicit"] = (
        timings["raw_sql"]
        + timings["events_sql"]
        + timings["two_map_mem"]
        + timings["two_build_mem"]
    )

    sig_join = _qfq_signature(join_e2e or join_built)
    sig_two = _qfq_signature(two_e2e or two_memory)

    return {
        "stock_id": stock_id,
        "bars": sig_join[0],
        "timings": timings,
        "sig_join": sig_join,
        "sig_two": sig_two,
        "sig_match": sig_join == sig_two,
        "event_count": len(events_rows),
    }


def print_summary(label: str, key: str, rows: List[Dict[str, Any]]) -> None:
    samples = [r["timings"][key] for r in rows if key in r["timings"]]
    s = _summarize(samples)
    print(
        f"| {label} | {s['median']:.2f} | {s['mean']:.2f} | {s['p95']:.2f} | {s['sum']:.0f} |"
    )


def main() -> None:
    dm = DataManager()
    svc = dm.stock.kline
    start = _actual_start()

    stocks = []
    for sid in SAMPLE_STOCKS:
        try:
            raw = svc.load_raw(sid, TERM, start, END)
            if raw:
                stocks.append(sid)
        except Exception:
            pass
    if not stocks:
        raise SystemExit("没有可用样本股票")

    print("=== QFQ 加载对比实验 ===")
    print(f"区间: {start} ~ {END}  term={TERM}  样本股数: {len(stocks)}")
    print()

    results = [bench_one_stock(svc, sid, start, END) for sid in stocks]
    mism = [r for r in results if not r["sig_match"]]
    print(f"结果一致性: {len(stocks) - len(mism)}/{len(stocks)} 股 sig 一致")
    if mism:
        for r in mism[:5]:
            print(f"  不一致: {r['stock_id']} join={r['sig_join']} two={r['sig_two']}")
    print()

    print("| 路径 (ms/股) | median | mean | p95 | sum(全样本) |")
    print("|---|--:|--:|--:|--:|")
    print_summary("JOIN 仅 SQL", "join_sql", results)
    print_summary("JOIN 仅 Python build", "join_build", results)
    print_summary("JOIN SQL+build", "join_total", results)
    print_summary("JOIN load_qfq 端到端", "join_e2e", results)
    print("| — | — | — | — | — |")
    print_summary("两步 raw SQL", "raw_sql", results)
    print_summary("两步 events SQL", "events_sql", results)
    print_summary("两步 SQL 合计", "two_sql_sum", results)
    print_summary("两步 map 内存", "two_map_mem", results)
    print_summary("两步 build 内存", "two_build_mem", results)
    print_summary("两步 显式 2SQL+map+build", "two_total_explicit", results)
    print_summary("两步 build (_build 内或再打DB)", "two_build_api", results)
    print_summary("两步 fallback 端到端", "two_e2e_fallback", results)

    j_med = statistics.median([r["timings"]["join_e2e"] for r in results])
    t_med = statistics.median([r["timings"]["two_e2e_fallback"] for r in results])
    e_med = statistics.median([r["timings"]["two_total_explicit"] for r in results])
    print()
    print("=== 结论（median/股）===")
    print(f"- load_qfq (大 JOIN 端到端): {j_med:.2f} ms")
    print(f"- fallback (raw + build 端到端): {t_med:.2f} ms  → 相对 JOIN {(t_med/j_med if j_med else 0):.2f}x")
    print(f"- 显式 2 SQL + 内存 build: {e_med:.2f} ms  → 相对 JOIN {(e_med/j_med if j_med else 0):.2f}x")

    j_sql = statistics.median([r["timings"]["join_sql"] for r in results])
    r_sql = statistics.median([r["timings"]["raw_sql"] for r in results])
    ev_sql = statistics.median([r["timings"]["events_sql"] for r in results])
    print()
    print("=== SQL 墙钟拆分（median/股）===")
    print(f"- JOIN 一条 SQL: {j_sql:.2f} ms")
    print(f"- raw + events 两条 SQL: {r_sql:.2f} + {ev_sql:.2f} = {r_sql + ev_sql:.2f} ms")


if __name__ == "__main__":
    main()
