#!/usr/bin/env python3
import sys
import os
import random
import argparse
from datetime import datetime, timedelta
from collections import defaultdict
import pandas as pd

# project root
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT)

from utils.db.db_manager import DatabaseManager
from app.data_source.data_source_service import DataSourceService
from app.data_source.providers.akshare.akshare_API_mod import AkshareAPIModified


def load_daily_k_lines(db, ts_code: str, start_date: str, end_date: str):
    stock_kline = db.get_table_instance('stock_klines')
    condition = "id = %s AND term = %s AND date >= %s AND date <= %s"
    params = (ts_code, 'daily', start_date, end_date)
    return stock_kline.load(condition, params, order_by="date ASC")


def load_qfq_factors(db, ts_code: str, start_date: str, end_date: str):
    adj_factor = db.get_table_instance('adj_factor')
    condition = "id = %s AND date >= %s AND date <= %s"
    params = (ts_code, start_date, end_date)
    return adj_factor.load(condition, params, order_by="date ASC")


def to_date_str_ymd(s: str) -> str:
    if '-' in s:
        return s.replace('-', '')
    return s


def to_date_hyphen(s: str) -> str:
    if '-' in s:
        return s
    return f"{s[:4]}-{s[4:6]}-{s[6:]}"


def get_quarter_key(date_str_hyphen: str) -> str:
    dt = datetime.strptime(date_str_hyphen, '%Y-%m-%d')
    q = (dt.month - 1) // 3 + 1
    return f"{dt.year}-Q{q}"


def compare_quarterly(ts_code: str, start_date: str, end_date: str, samples_per_quarter: int = 1, seed: int = 42, output_csv: str = None):
    random.seed(seed)
    db = DatabaseManager()

    k_lines = load_daily_k_lines(db, ts_code, start_date, end_date)
    factors = load_qfq_factors(db, ts_code, start_date, end_date)

    if not k_lines:
        print(f"No local k_lines for {ts_code} in [{start_date}, {end_date}]")
        return
    if not factors:
        print(f"No factors for {ts_code} in [{start_date}, {end_date}]")
        return

    # compute our qfq for OHLC
    k_lines_copy = [dict(x) for x in k_lines]
    our_qfq_lines = DataSourceService.to_qfq(k_lines_copy, factors)

    def safe_float(v):
        try:
            return float(v) if v is not None else None
        except Exception:
            return None

    our_by_date = {}
    for x in our_qfq_lines:
        d = to_date_hyphen(x['date'])
        our_by_date[d] = {
            'open': safe_float(x.get('open')),
            'close': safe_float(x.get('close')),
            'high': safe_float(x.get('highest')),
            'low': safe_float(x.get('lowest')),
        }

    # akshare qfq
    ak = AkshareAPIModified(is_verbose=False)
    ak_df = ak.get_k_lines(stock_id=ts_code, period='daily', start_date=start_date, end_date=end_date, adjust='qfq')
    if ak_df is None or ak_df.empty:
        print(f"AKShare returned empty data for {ts_code}")
        return
    ak_df = ak_df.copy()
    ak_df['date'] = pd.to_datetime(ak_df['日期']).dt.strftime('%Y-%m-%d')
    ak_by_date = {row['date']: {'open': float(row['开盘']), 'close': float(row['收盘']), 'high': float(row['最高']), 'low': float(row['最低'])} for _, row in ak_df.iterrows()}

    # overlap dates
    common_dates = sorted(set(our_by_date.keys()) & set(ak_by_date.keys()))
    if not common_dates:
        print("No overlapping dates between local and AKShare")
        return

    # group by quarter and sample dates
    quarter_to_dates = defaultdict(list)
    for d in common_dates:
        quarter_to_dates[get_quarter_key(d)].append(d)

    rows = []
    for q, dates in sorted(quarter_to_dates.items()):
        if not dates:
            continue
        # ensure unique random picks up to available
        picks = min(samples_per_quarter, len(dates))
        sampled = random.sample(dates, picks)
        for sampled_date in sampled:
            our_vals = our_by_date[sampled_date]
            ak_vals = ak_by_date[sampled_date]
            def diff_pair(key):
                our_v = our_vals[key]
                ak_v = ak_vals[key]
                abs_diff = (our_v - ak_v) if (our_v is not None and ak_v is not None) else None
                pct_diff = ((abs_diff / ak_v) * 100) if (abs_diff is not None and ak_v != 0) else None
                return our_v, ak_v, abs_diff, pct_diff
            o_open, a_open, d_open, p_open = diff_pair('open')
            o_close, a_close, d_close, p_close = diff_pair('close')
            o_high, a_high, d_high, p_high = diff_pair('high')
            o_low, a_low, d_low, p_low = diff_pair('low')
            rows.append({
                'ts_code': ts_code,
                'quarter': q,
                'date': sampled_date,
                'our_open': o_open, 'ak_open': a_open, 'abs_diff_open': d_open, 'pct_diff_open': p_open,
                'our_close': o_close, 'ak_close': a_close, 'abs_diff_close': d_close, 'pct_diff_close': p_close,
                'our_high': o_high, 'ak_high': a_high, 'abs_diff_high': d_high, 'pct_diff_high': p_high,
                'our_low': o_low, 'ak_low': a_low, 'abs_diff_low': d_low, 'pct_diff_low': p_low,
            })

    if not rows:
        print("No sampled rows")
        return

    df = pd.DataFrame(rows)

    # print report (close-focused)
    print(f"Quarterly QFQ OHLC comparison for {ts_code} [{start_date} ~ {end_date}] ({samples_per_quarter} sample(s) per quarter)")
    print("quarter,date,our_close,akshare_close,abs_diff_close,pct_diff_close(%)")
    for _, r in df.sort_values(['quarter', 'date']).iterrows():
        print(f"{r['quarter']},{r['date']},{round(r['our_close'],6) if pd.notna(r['our_close']) else 'NA'},{round(r['ak_close'],6) if pd.notna(r['ak_close']) else 'NA'},{round(r['abs_diff_close'],6) if pd.notna(r['abs_diff_close']) else 'NA'},{round(r['pct_diff_close'],6) if pd.notna(r['pct_diff_close']) else 'NA'}")

    # summary (close)
    val = df['abs_diff_close'].dropna()
    valp = df['pct_diff_close'].dropna()
    if not val.empty:
        print("\nsummary (close):")
        print(f"count={len(val)}, abs_diff: mean={round(val.mean(),6)}, max={round(val.iloc[val.abs().argmax()],6)}")
        print(f"pct_diff%: mean={round(valp.mean(),6)}%, max={round(valp.iloc[valp.abs().argmax()],6)}%")

    # optional CSV export
    if output_csv:
        out_path = output_csv
        # add timestamp if directory provided
        if os.path.isdir(output_csv):
            out_path = os.path.join(output_csv, f"qfq_compare_{ts_code}_{start_date}_{end_date}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        df.to_csv(out_path, index=False)
        print(f"\nCSV written: {out_path}")


def main():
    parser = argparse.ArgumentParser(description='Compare our QFQ OHLC vs AKShare by sampling per quarter')
    parser.add_argument('ts_code', help='TS code, e.g., 000001.SZ')
    parser.add_argument('start_date', nargs='?', help='YYYYMMDD')
    parser.add_argument('end_date', nargs='?', help='YYYYMMDD')
    parser.add_argument('--samples', type=int, default=1, help='Samples per quarter (default: 1)')
    parser.add_argument('--seed', type=int, default=42, help='Random seed (default: 42)')
    parser.add_argument('--output', help='CSV output file or directory (optional)')
    args = parser.parse_args()

    if args.start_date and args.end_date:
        start_date = args.start_date
        end_date = args.end_date
    else:
        end_dt = datetime.today()
        start_dt = end_dt - timedelta(days=365*3)
        start_date = start_dt.strftime('%Y%m%d')
        end_date = end_dt.strftime('%Y%m%d')

    compare_quarterly(args.ts_code, start_date, end_date, samples_per_quarter=args.samples, seed=args.seed, output_csv=args.output)


if __name__ == '__main__':
    main()
