#!/usr/bin/env python3
"""
导出 5 只股票 腾讯 API（stock_zh_a_hist_tx）前复权收盘价，
供人工与东方财富网站对比，验证两者是否一致。

股票：000001.SZ, 000333.SZ, 600036.SH, 000651.SZ, 300274.SZ
时间段：2024-01-02 ~ 2024-01-31

东方财富查看路径：quote.eastmoney.com -> 输入股票代码 -> K线 -> 前复权
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

STOCKS = ["000001.SZ", "000333.SZ", "600036.SH", "000651.SZ", "300274.SZ"]
START = "20240102"
END = "20240131"


def tushare_to_tx_symbol(stock_id: str) -> str:
    """000001.SZ -> sz000001, 600000.SH -> sh600000"""
    if "." not in stock_id:
        return stock_id
    code, market = stock_id.split(".")
    if market == "SZ":
        return f"sz{code}"
    elif market == "SH":
        return f"sh{code}"
    elif market == "BJ":
        return f"bj{code}"
    return stock_id


def fetch_tencent_qfq(stock_id: str, start_date: str, end_date: str) -> list:
    """腾讯 stock_zh_a_hist_tx 前复权收盘价，返回 [(date_ymd, close), ...]"""
    import akshare as ak
    tx_symbol = tushare_to_tx_symbol(stock_id)
    df = ak.stock_zh_a_hist_tx(
        symbol=tx_symbol,
        start_date=start_date,
        end_date=end_date,
        adjust="qfq",
    )
    if df is None or df.empty:
        return []
    date_col = "日期" if "日期" in df.columns else "date"
    close_col = "收盘" if "收盘" in df.columns else "close"
    result = []
    for _, row in df.iterrows():
        d = str(row.get(date_col, ""))
        d_ymd = d.replace("-", "") if d else ""
        if len(d_ymd) == 8 and d_ymd.isdigit():
            c = float(row.get(close_col, 0))
            if c > 0:
                result.append((d_ymd, c))
    result.sort(key=lambda x: x[0])
    return result


def main():
    print("=" * 60)
    print("腾讯 API（stock_zh_a_hist_tx）前复权收盘价")
    print("供人工与东方财富 quote.eastmoney.com 对比")
    print("=" * 60)
    print("东方财富：K线 -> 前复权")
    print("")

    for stock_id in STOCKS:
        rows = fetch_tencent_qfq(stock_id, START, END)
        if not rows:
            print(f"{stock_id}: 无数据\n")
            continue

        print(f"--- {stock_id} ---")
        print("日期         qfq_close(腾讯)")
        for d_ymd, c in rows:
            d_fmt = d_ymd[:4] + "-" + d_ymd[4:6] + "-" + d_ymd[6:8]
            print(f"{d_fmt}   {c:.4f}")
        print()

    print("=" * 60)

    # 导出 CSV
    out_path = os.path.join(os.path.dirname(__file__), "tencent_qfq_for_eastmoney_compare.csv")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("stock_id,date,qfq_close_tencent\n")
        for stock_id in STOCKS:
            rows = fetch_tencent_qfq(stock_id, START, END)
            for d_ymd, c in rows:
                d_fmt = d_ymd[:4] + "-" + d_ymd[4:6] + "-" + d_ymd[6:8]
                f.write(f"{stock_id},{d_fmt},{c:.4f}\n")
    print(f"\n已导出 CSV: tencent_qfq_for_eastmoney_compare.csv")


if __name__ == "__main__":
    main()
