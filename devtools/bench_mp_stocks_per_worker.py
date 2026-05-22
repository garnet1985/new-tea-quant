#!/usr/bin/env python3
"""
多进程对比（修正版）：

- 1 股/job：每股独立 DB 往返（load_qfq = 1 条 JOIN SQL / 股）
- 3 股/job：每 job 仅 2 次批量 SQL（K 线 IN + 复权事件 IN）+ 内存算 QFQ

用法:
  PYTHONPATH=. python3 devtools/bench_mp_stocks_per_worker.py
"""
from __future__ import annotations

import multiprocessing as mp
import statistics
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Any, Dict, List

from core.infra.worker.multi_process.process_worker import ProcessWorker
from core.modules.data_manager import DataManager
from core.utils.date.date_utils import DateUtils

START = "20240307"
END = "20251231"
LOOKBACK = 30
TERM = "daily"
STOCKS_PER_JOB_MULTI = 3
REPEATS = 2

CANDIDATES = [
    "000858.SZ", "000002.SZ", "000937.SZ", "000725.SZ", "002032.SZ",
    "000776.SZ", "001289.SZ", "000999.SZ", "600519.SH", "000001.SZ",
    "601318.SH", "300750.SZ", "688981.SH", "002594.SZ", "600036.SH",
    "000333.SZ", "601012.SH", "002415.SZ", "000063.SZ", "600900.SH",
    "601166.SH", "000651.SZ", "002304.SZ", "600276.SH", "000568.SZ",
    "601888.SH", "002142.SZ", "600030.SH", "601398.SH", "000792.SZ",
    "002230.SZ", "600887.SH", "000338.SZ", "601288.SH", "002352.SZ",
    "600050.SH", "000100.SZ", "601857.SH", "002241.SZ", "600104.SH",
    "000625.SZ", "601328.SH", "002475.SZ", "600019.SH", "000538.SZ",
    "601939.SH", "002460.SZ", "600585.SH", "000768.SZ", "601988.SH",
    "002714.SZ", "600309.SH", "000977.SZ", "601628.SH", "002493.SZ",
    "600196.SH", "000963.SZ", "601009.SH",
]


def _actual_start() -> str:
    return DateUtils.sub_days(START, LOOKBACK)


def _discover_stock_pool() -> List[str]:
    dm = DataManager()
    svc = dm.stock.kline
    start = _actual_start()
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


def _memory_qfq_for_stock(svc: Any, stock_id: str, raw_rows: List[Dict[str, Any]], events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """批量拉事件后，单股内存复权（不再打 DB）。"""
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
                "event": None,
                "qfq_diff": 0.0,
                "is_adjusted": False,
                "is_inferred": False,
            }
        else:
            qfq_diff = float(selected.get("qfq_diff", 0.0) or 0.0)
            event_map[d] = {
                "event": selected,
                "qfq_diff": qfq_diff,
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


def _load_single_stock_io(svc: Any, stock_id: str, start: str, end: str) -> Dict[str, Any]:
    """每股 1 次 load_qfq（JOIN SQL）。"""
    t0 = time.perf_counter()
    rows = svc.load_qfq(stock_id, TERM, start, end)
    ms = (time.perf_counter() - t0) * 1000.0
    return {
        "stock_id": stock_id,
        "bars": len(rows or []),
        "sql_queries": 1,
        "sql_ms": ms,
        "qfq_cpu_ms": 0.0,
    }


def _load_batch_io(svc: Any, stock_ids: List[str], start: str, end: str) -> Dict[str, Any]:
    """每 job：K 线 1 query + 复权事件 1 query + 内存 QFQ。"""
    if not stock_ids:
        return {"sql_queries": 0, "sql_ms": 0.0, "qfq_cpu_ms": 0.0, "bars": 0}

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

    sql_queries = 0
    sql_ms = 0.0

    t0 = time.perf_counter()
    raw_all = svc._stock_kline.load(where_k, tuple(params), order_by="id ASC, date ASC") or []
    sql_ms += (time.perf_counter() - t0) * 1000.0
    sql_queries += 1

    raw_by_stock = _group_by_id(raw_all, stock_ids)

    t0 = time.perf_counter()
    events_all: List[Dict[str, Any]] = []
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
    sql_queries += 1

    events_by_stock = _group_by_id(events_all, stock_ids)

    t0 = time.perf_counter()
    total_bars = 0
    for sid in stock_ids:
        qfq_rows = _memory_qfq_for_stock(
            svc, sid, raw_by_stock.get(sid) or [], events_by_stock.get(sid) or []
        )
        total_bars += len(qfq_rows)
    qfq_cpu_ms = (time.perf_counter() - t0) * 1000.0

    return {
        "sql_queries": sql_queries,
        "sql_ms": sql_ms,
        "qfq_cpu_ms": qfq_cpu_ms,
        "bars": total_bars,
        "stocks": len(stock_ids),
    }


def _mp_worker(payload: Dict[str, Any]) -> Dict[str, Any]:
    if mp.current_process().name != "MainProcess":
        try:
            from core.infra.db import DatabaseManager

            DatabaseManager.reset_default()
        except Exception:
            pass

    mode = str(payload.get("mode") or "single")
    stock_ids = list(payload.get("stock_ids") or [])
    start = str(payload["start"])
    end = str(payload["end"])

    dm = DataManager()
    svc = dm.stock.kline

    if mode == "batch":
        stats = _load_batch_io(svc, stock_ids, start, end)
        return {"mode": mode, "stock_ids": stock_ids, **stats}

    sql_queries = 0
    sql_ms = 0.0
    bars = 0
    for sid in stock_ids:
        one = _load_single_stock_io(svc, sid, start, end)
        sql_queries += int(one["sql_queries"])
        sql_ms += float(one["sql_ms"])
        bars += int(one["bars"])

    return {
        "mode": mode,
        "stock_ids": stock_ids,
        "sql_queries": sql_queries,
        "sql_ms": sql_ms,
        "qfq_cpu_ms": 0.0,
        "bars": bars,
        "stocks": len(stock_ids),
    }


def _chunk(items: List[str], size: int) -> List[List[str]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def _build_jobs(stocks: List[str], stocks_per_job: int, start: str, mode: str) -> List[Dict[str, Any]]:
    groups = [[s] for s in stocks] if stocks_per_job <= 1 else _chunk(stocks, stocks_per_job)
    return [
        {
            "id": f"job-{i}",
            "payload": {
                "mode": mode,
                "stock_ids": g,
                "start": start,
                "end": END,
            },
        }
        for i, g in enumerate(groups)
    ]


def _run_scenario(
    *,
    label: str,
    stocks: List[str],
    stocks_per_job: int,
    mode: str,
    max_workers: int,
    start: str,
) -> Dict[str, Any]:
    jobs = _build_jobs(stocks, stocks_per_job, start, mode)
    wall_t0 = time.perf_counter()
    sql_queries = 0
    sql_ms = 0.0
    qfq_cpu_ms = 0.0
    bars = 0

    ctx = mp.get_context("spawn")
    with ProcessPoolExecutor(max_workers=max_workers, mp_context=ctx) as pool:
        futures = [pool.submit(_mp_worker, j["payload"]) for j in jobs]
        for fut in as_completed(futures):
            r = fut.result()
            sql_queries += int(r.get("sql_queries") or 0)
            sql_ms += float(r.get("sql_ms") or 0)
            qfq_cpu_ms += float(r.get("qfq_cpu_ms") or 0)
            bars += int(r.get("bars") or 0)

    wall_s = time.perf_counter() - wall_t0
    stocks_n = len(stocks)
    return {
        "label": label,
        "mode": mode,
        "stocks": stocks_n,
        "jobs": len(jobs),
        "stocks_per_job": stocks_per_job,
        "sql_queries_total": sql_queries,
        "sql_per_stock": sql_queries / stocks_n if stocks_n else 0,
        "sql_ms_sum": sql_ms,
        "qfq_cpu_ms_sum": qfq_cpu_ms,
        "wall_s": wall_s,
        "bars": bars,
    }


def main() -> None:
    stocks = _discover_stock_pool()
    n = (len(stocks) // STOCKS_PER_JOB_MULTI) * STOCKS_PER_JOB_MULTI
    stocks = stocks[:n]
    if n < 6:
        raise SystemExit(f"样本不足: {n}")

    start = _actual_start()
    max_workers = ProcessWorker.resolve_max_workers("auto", "OpportunityEnumerator")

    print("=== 多进程 IO 对比（修正）===")
    print(f"股票 {n} 只 | {start}~{END} | workers={max_workers} | spawn")
    print()
    print("A) 1股/job: 每股 1× load_qfq (JOIN SQL)")
    print("B) 3股/job: 1× K线IN + 1× 复权IN + 内存QFQ（每 job 仅 2 次 SQL）")
    print()

    rows: List[Dict[str, Any]] = []
    for rep in range(1, REPEATS + 1):
        print(f"--- 第 {rep} 轮 ---")
        a = _run_scenario(
            label="1股/job JOIN",
            stocks=stocks,
            stocks_per_job=1,
            mode="single",
            max_workers=max_workers,
            start=start,
        )
        b = _run_scenario(
            label="3股/job 批量IO",
            stocks=stocks,
            stocks_per_job=STOCKS_PER_JOB_MULTI,
            mode="batch",
            max_workers=max_workers,
            start=start,
        )
        rows.extend([a, b])
        print(
            f"  A wall={a['wall_s']:.2f}s sql={a['sql_queries_total']}次 "
            f"({a['sql_per_stock']:.2f}/股) sql_ms={a['sql_ms_sum']:.0f}"
        )
        print(
            f"  B wall={b['wall_s']:.2f}s sql={b['sql_queries_total']}次 "
            f"({b['sql_per_stock']:.2f}/股) sql_ms={b['sql_ms_sum']:.0f} "
            f"qfq_cpu={b['qfq_cpu_ms_sum']:.0f}ms"
        )
        print(f"  墙钟 B/A={b['wall_s']/a['wall_s']:.3f}x  SQL次数 B/A={b['sql_queries_total']/a['sql_queries_total']:.3f}x")
        print()

    a_wall = statistics.median([r["wall_s"] for r in rows if r["mode"] == "single"])
    b_wall = statistics.median([r["wall_s"] for r in rows if r["mode"] == "batch"])
    a_sql = statistics.median([r["sql_queries_total"] for r in rows if r["mode"] == "single"])
    b_sql = statistics.median([r["sql_queries_total"] for r in rows if r["mode"] == "batch"])

    print("=== median 汇总 ===")
    print(f"A 墙钟 {a_wall:.2f}s | SQL {int(a_sql)} 次 ({n} 次/股)")
    print(f"B 墙钟 {b_wall:.2f}s | SQL {int(b_sql)} 次 ({b_sql/n:.2f} 次/股)")
    print(f"墙钟比 B/A={b_wall/a_wall:.3f}x | SQL 比 B/A={b_sql/a_sql:.3f}x")
    print()
    print("理论 SQL：A=每股1次→N次；B=每3股2次→约 2N/3 次")


if __name__ == "__main__":
    main()
