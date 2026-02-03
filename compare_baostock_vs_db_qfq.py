#!/usr/bin/env python3
"""
对比 Baostock 前复权价格 vs DB load_qfq 价格

随机选 3 只股票、1 个时间段，比较两者的前复权收盘价差异。
"""
import sys
import os
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def tushare_to_baostock(stock_id: str) -> str:
    """000001.SZ -> sz.000001, 600000.SH -> sh.600000"""
    if "." not in stock_id:
        return stock_id
    code, market = stock_id.split(".")
    if market == "SZ":
        return f"sz.{code}"
    elif market == "SH":
        return f"sh.{code}"
    elif market == "BJ":
        return f"bj.{code}"
    return stock_id


def fetch_baostock_qfq(stock_id: str, start_date: str, end_date: str) -> dict:
    """从 Baostock 获取前复权收盘价，返回 {date_ymd: close}"""
    try:
        import baostock as bs
    except ImportError:
        return {}
    # Baostock 需要 YYYY-MM-DD 格式
    start_ymd = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:8]}" if len(start_date) == 8 else start_date
    end_ymd = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:8]}" if len(end_date) == 8 else end_date
    bs_code = tushare_to_baostock(stock_id)
    lg = bs.login()
    if lg.error_code != "0":
        return {}
    rs = bs.query_history_k_data_plus(
        bs_code,
        "date,close",
        start_date=start_ymd,
        end_date=end_ymd,
        frequency="d",
        adjustflag="2",
    )
    if rs is None or rs.error_code != "0":
        bs.logout()
        return {}
    result = {}
    while rs.next():
        row = rs.get_row_data()
        if row and len(row) >= 2:
            date_str = row[0].replace("-", "")  # YYYY-MM-DD -> YYYYMMDD
            result[date_str] = float(row[1])
    bs.logout()
    return result


def main():
    # 3 只股票，1 个随机时间段
    stocks = ["000001.SZ", "600000.SH", "000002.SZ"]  # 平安银行、浦发银行、万科A
    periods = [
        ("2023-06-01", "2023-06-30"),
        ("2023-08-01", "2023-08-31"),
        ("2024-01-02", "2024-01-31"),
    ]
    start_date, end_date = random.choice(periods)
    start_ymd = start_date.replace("-", "")
    end_ymd = end_date.replace("-", "")

    print("=" * 70)
    print("Baostock 前复权 vs DB load_qfq 价格对比")
    print("=" * 70)
    print(f"股票: {stocks}")
    print(f"时间段: {start_date} ~ {end_date}")
    print()

    # 初始化 DataManager
    from core.modules.data_manager import DataManager

    data_mgr = DataManager(is_verbose=False)
    data_mgr.initialize()

    for stock_id in stocks:
        print(f"\n--- {stock_id} ---")

        # Baostock
        bs_map = fetch_baostock_qfq(stock_id, start_ymd, end_ymd)
        if not bs_map:
            print(f"  Baostock: 无数据")
            continue
        print(f"  Baostock: {len(bs_map)} 条")

        # DB load_qfq
        try:
            db_klines = data_mgr.stock.kline.load_qfq(
                stock_id, term="daily", start_date=start_ymd, end_date=end_ymd
            )
        except Exception as e:
            print(f"  DB load_qfq: 错误 {e}")
            continue

        db_map = {}
        for row in db_klines:
            d = row.get("date")
            if d:
                d_ymd = str(d).replace("-", "")
                qfq_close = row.get("qfq_close")
                if qfq_close is not None:
                    db_map[d_ymd] = float(qfq_close)

        if not db_map:
            print(f"  DB load_qfq: 无数据")
            continue
        print(f"  DB load_qfq: {len(db_map)} 条")

        # 对比共同日期
        common_dates = sorted(set(bs_map.keys()) & set(db_map.keys()))
        if not common_dates:
            print(f"  共同日期: 0")
            continue

        diffs = []
        for d in common_dates:
            bs_p = bs_map[d]
            db_p = db_map[d]
            diff = db_p - bs_p
            diff_pct = (diff / bs_p * 100) if bs_p else 0
            diffs.append((d, bs_p, db_p, diff, diff_pct))

        # 输出前 5 条 + 统计
        print(f"  共同日期: {len(common_dates)} 天")
        print(f"  {'日期':<10} {'Baostock':>10} {'DB':>10} {'差值':>10} {'差值%':>8}")
        print("  " + "-" * 52)
        for d, bs_p, db_p, diff, pct in diffs[:5]:
            print(f"  {d}  {bs_p:>10.4f} {db_p:>10.4f} {diff:>+10.4f} {pct:>+7.3f}%")
        if len(diffs) > 5:
            print("  ...")
        avg_diff = sum(x[3] for x in diffs) / len(diffs)
        max_diff = max(abs(x[3]) for x in diffs)
        avg_pct = sum(x[4] for x in diffs) / len(diffs)
        print(f"  平均差值: {avg_diff:+.4f}, 最大绝对差值: {max_diff:.4f}, 平均差值%: {avg_pct:+.3f}%")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
