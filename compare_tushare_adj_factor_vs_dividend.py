#!/usr/bin/env python3
"""
直接对比 Tushare 同一只股票的：
1. adj_factor 复权因子变化日
2. dividend 除权除息日 ex_date

验证：复权因子变化的那天是否就是除权除息日。
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def get_tushare_token():
    from core.infra.project_context import PathManager

    p = PathManager.data_source_provider("tushare") / "auth_token.txt"
    if p.exists():
        return open(p).read().strip()
    return os.getenv("TUSHARE_TOKEN")


def get_adj_factor_changing_dates(ts_code: str, token: str, start_date: str = "20240101", end_date: str = "20251231"):
    """Tushare adj_factor API -> 因子变化日"""
    import tushare as ts
    import pandas as pd

    ts.set_token(token)
    df = ts.pro_api().adj_factor(ts_code=ts_code, start_date=start_date, end_date=end_date)
    if df is None or df.empty:
        return []

    df = df.sort_values("trade_date", ascending=True)
    changing = []
    prev = None
    for _, row in df.iterrows():
        f = float(row.get("adj_factor", 0))
        d = str(row.get("trade_date", ""))
        if not d:
            continue
        if prev is not None and abs(f - prev) > 1e-6:
            changing.append(d)
        prev = f
    return changing


def get_dividend_ex_dates(ts_code: str, token: str, start_date: str = "20240101", end_date: str = "20251231"):
    """Tushare dividend API -> 除权除息日 ex_date"""
    import tushare as ts
    import pandas as pd

    ts.set_token(token)
    df = ts.pro_api().dividend(ts_code=ts_code, fields="ts_code,ex_date,end_date")
    if df is None or df.empty:
        return []

    ex_dates = []
    for _, row in df.iterrows():
        ex = row.get("ex_date")
        if pd.isna(ex):
            continue
        d = str(ex).replace("-", "")[:8]
        if len(d) == 8 and d.isdigit() and start_date <= d <= end_date:
            ex_dates.append(d)
    return sorted(set(ex_dates))


def main():
    token = get_tushare_token()
    if not token:
        print("❌ 需设置 TUSHARE_TOKEN 或 auth_token.txt")
        return

    ts_code = sys.argv[1] if len(sys.argv) > 1 else "000001.SZ"
    start, end = "20240101", "20251231"

    print("=" * 60)
    print(f"股票: {ts_code}  时间段: {start} ~ {end}")
    print("=" * 60)

    adj_dates = get_adj_factor_changing_dates(ts_code, token, start, end)
    ex_dates = get_dividend_ex_dates(ts_code, token, start, end)

    print(f"\n复权因子变化日 (adj_factor): {adj_dates}")
    print(f"除权除息日 (dividend.ex_date): {ex_dates}")

    adj_set = set(adj_dates)
    ex_set = set(ex_dates)
    match = adj_set & ex_set
    adj_only = adj_set - ex_set
    ex_only = ex_set - adj_set

    print("\n" + "-" * 60)
    print(f"完全一致: {sorted(match)}")
    if adj_only:
        print(f"仅 adj 有: {sorted(adj_only)}")
    if ex_only:
        print(f"仅 ex_date 有: {sorted(ex_only)}")

    all_match = not adj_only and not ex_only and (adj_set or ex_set)
    print("-" * 60)
    print(f"结论: {'✓ 复权因子变化日 = 除权除息日' if all_match else '△ 有差异'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
