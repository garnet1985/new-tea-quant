#!/usr/bin/env python3
"""
对比 Tushare dividend API（ex_date 除权除息日）与 DB/CSV 复权事件 event_date

限定时间段（默认 2024-2025）验证：DB 的 event_date 来自 Tushare adj_factor 变化点，
理论上应与 Tushare dividend.ex_date 能对上。

数据源优先级：CSV（若存在）> DB
"""
import sys
import os
import glob
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 对比时间段
START_YMD = "20240101"
END_YMD = "20251231"


def get_tushare_token():
    """从文件或环境变量获取 Tushare token"""
    from core.infra.project_context import PathManager

    auth_token_path = PathManager.data_source_provider("tushare") / "auth_token.txt"
    if auth_token_path.exists():
        with open(auth_token_path, "r") as f:
            return f.read().strip()
    return os.getenv("TUSHARE_TOKEN")


def _in_range(ymd: str) -> bool:
    """事件日期是否在 2024-2025 范围内"""
    y = ymd.replace("-", "")[:8]
    return len(y) == 8 and y.isdigit() and START_YMD <= y <= END_YMD


def load_csv_events_in_range(csv_dir_or_pattern: str) -> dict:
    """
    从 CSV 加载 2024-2025 的复权事件
    返回 {stock_id: {event_date_ymd, ...}}
    """
    import pandas as pd

    result = {}
    # 支持目录或通配符
    if os.path.isdir(csv_dir_or_pattern):
        pattern = os.path.join(csv_dir_or_pattern, "adj_factor_events_*.csv")
    else:
        pattern = csv_dir_or_pattern

    files = sorted(glob.glob(pattern))
    # 只取 2024、2025 季度的 CSV
    for f in files:
        name = os.path.basename(f)
        if "2024" not in name and "2025" not in name:
            continue
        try:
            df = pd.read_csv(f)
            if "id" not in df.columns or "event_date" not in df.columns:
                continue
            for _, row in df.iterrows():
                sid = str(row.get("id", "")).strip()
                ed = str(row.get("event_date", "")).replace("-", "")[:8]
                if not sid or len(ed) != 8 or not ed.isdigit():
                    continue
                if not _in_range(ed):
                    continue
                result.setdefault(sid, set()).add(ed)
        except Exception:
            continue
    return result


def find_csv_dir() -> str:
    """查找 adj_factor_events CSV 所在目录"""
    root = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(root, "userspace", "data_source", "handlers", "adj_factor_event"),
        os.path.join(root, "core", "modules", "data_source", "handlers", "adj_factor_event"),
    ]
    for d in candidates:
        if os.path.isdir(d):
            g = glob.glob(os.path.join(d, "adj_factor_events_*.csv"))
            if g:
                return d
    return ""


def fetch_tushare_dividend_ex_dates(ts_code: str, token: str) -> set:
    """
    从 Tushare dividend API 获取除权除息日 ex_date（仅 2024-2025）
    返回 {YYYYMMDD, ...} 集合
    """
    try:
        import tushare as ts
        import pandas as pd
    except ImportError:
        return set()

    ts.set_token(token)
    pro = ts.pro_api()

    try:
        df = pro.dividend(
            ts_code=ts_code,
            fields="ts_code,div_proc,ex_date,end_date",
        )
    except Exception as e:
        print(f"    Tushare dividend API 失败: {e}")
        return set()

    if df is None or df.empty:
        return set()

    ex_dates = set()
    for _, row in df.iterrows():
        ex_val = row.get("ex_date")
        if pd.isna(ex_val) or ex_val is None:
            continue
        ex_str = str(ex_val).strip()
        ex_ymd = ex_str.replace("-", "")[:8]
        if len(ex_ymd) == 8 and ex_ymd.isdigit() and _in_range(ex_ymd):
            ex_dates.add(ex_ymd)
    return ex_dates


def load_db_adj_event_dates_in_range(data_mgr, stock_id: str) -> set:
    """
    从 DB 加载 2024-2025 内的 event_date
    """
    adj_model = data_mgr.stock.kline._adj_factor_event
    if not adj_model:
        return set()
    events = adj_model.load_by_date_range(stock_id, START_YMD, END_YMD)
    return {str(e.get("event_date", "")).replace("-", "")[:8] for e in events if e.get("event_date")}


def get_stocks_and_db_events_in_range(data_mgr):
    """从 DB 获取 2024-2025 内有事件的股票及事件日期"""
    adj_model = data_mgr.stock.kline._adj_factor_event
    if not adj_model:
        return {}, []
    try:
        rows = adj_model.execute_raw_query(
            "SELECT DISTINCT id FROM sys_adj_factor_events "
            "WHERE event_date >= %s AND event_date <= %s ORDER BY id",
            (START_YMD, END_YMD),
        )
        stocks = [r["id"] for r in rows if r.get("id")][:18]  # 限制数量避免超时
        result = {}
        for sid in stocks:
            result[sid] = load_db_adj_event_dates_in_range(data_mgr, sid)
        return result, stocks
    except Exception as e:
        print(f"  [WARN] DB 查询失败: {e}")
        return {}, []


def main():
    print("=" * 70)
    print("Tushare dividend.ex_date vs DB/CSV 复权事件 event_date")
    print(f"  时间段: {START_YMD} ~ {END_YMD} (2024-2025)")
    print("=" * 70)

    token = get_tushare_token()
    if not token:
        print("❌ 无法获取 Tushare token")
        print("   请设置: userspace/data_source/providers/tushare/auth_token.txt 或 环境变量 TUSHARE_TOKEN")
        return

    from core.modules.data_manager import DataManager

    data_mgr = DataManager(is_verbose=False)
    data_mgr.initialize()

    # 数据源：优先 CSV，否则 DB
    source_name = "DB"
    db_events_by_stock = {}
    csv_dir = find_csv_dir()
    if csv_dir:
        csv_events = load_csv_events_in_range(csv_dir)
        if csv_events:
            db_events_by_stock = csv_events
            source_name = "CSV"
            print(f"  数据源: CSV ({csv_dir})")
    if not db_events_by_stock:
        db_events_by_stock, stocks = get_stocks_and_db_events_in_range(data_mgr)
        if not stocks:
            # 若无 2024-2025 内事件，则从全表取有事件的股票，再按日期过滤
            try:
                rows = data_mgr.stock.kline._adj_factor_event.execute_raw_query(
                    "SELECT DISTINCT id FROM sys_adj_factor_events ORDER BY id LIMIT 50",
                    (),
                )
                stocks = [r["id"] for r in rows if r.get("id")]
                for sid in stocks:
                    db_events_by_stock[sid] = load_db_adj_event_dates_in_range(data_mgr, sid)
            except Exception:
                stocks = []
        else:
            stocks = list(db_events_by_stock.keys())
        print(f"  数据源: {source_name}")

    # 只保留该时间段内有事件的股票
    stocks = [s for s in db_events_by_stock if db_events_by_stock[s]]
    if not stocks:
        print("  无 2024-2025 内的复权事件数据，无法对比")
        return

    print(f"  股票数: {len(stocks)} (均有 2024-2025 内事件)")
    print()

    summary = []
    for i, stock_id in enumerate(stocks):
        if i > 0:
            time.sleep(0.15)  # 避免 Tushare 限流
        db_dates = db_events_by_stock.get(stock_id, set())
        ts_dates = fetch_tushare_dividend_ex_dates(stock_id, token)

        match = db_dates & ts_dates
        db_only = db_dates - ts_dates
        ts_only = ts_dates - db_dates

        summary.append(
            {
                "stock_id": stock_id,
                "db_count": len(db_dates),
                "ts_count": len(ts_dates),
                "match_count": len(match),
                "db_only": db_only,
                "ts_only": ts_only,
                "match": match,
            }
        )

    # 输出
    print("-" * 70)
    print(f"  {'股票':<12} {'事件数':>6} {'TS-ex':>6} {'命中':>6}  {'仅DB':>8} {'仅TS':>8}  状态")
    print("-" * 70)

    perfect = 0
    partial = 0
    mismatch = 0

    for s in summary:
        sid = s["stock_id"]
        db_n = s["db_count"]
        ts_n = s["ts_count"]
        match_n = s["match_count"]
        db_only_n = len(s["db_only"])
        ts_only_n = len(s["ts_only"])

        if db_n == 0 and ts_n == 0:
            status = "— 无数据"
        elif db_n == 0:
            status = "DB无"
        elif ts_n == 0:
            status = "TS无"
        elif db_only_n == 0 and ts_only_n == 0:
            status = "✓ 完全一致"
            perfect += 1
        elif db_only_n == 0 and ts_only_n > 0:
            status = "△ TS多"
            partial += 1
        elif db_only_n > 0 and ts_only_n == 0:
            status = "△ DB多"
            partial += 1
        else:
            status = "⚠ 有差异"
            mismatch += 1

        print(f"  {sid:<12} {db_n:>6} {ts_n:>6} {match_n:>6} {db_only_n:>8} {ts_only_n:>8}  {status}")

    print("-" * 70)
    print(f"  完全一致: {perfect}  部分差异: {partial}  有差异: {mismatch}")
    print("=" * 70)

    # 若有差异，输出详情
    has_detail = any(len(s["db_only"]) > 0 or len(s["ts_only"]) > 0 for s in summary)
    if has_detail:
        print("\n差异详情（仅DB / 仅TS）:")
        for s in summary:
            if s["db_only"] or s["ts_only"]:
                print(f"  {s['stock_id']}:")
                if s["db_only"]:
                    print(f"    仅DB: {sorted(s['db_only'])}")
                if s["ts_only"]:
                    print(f"    仅TS: {sorted(s['ts_only'])}")


if __name__ == "__main__":
    main()
