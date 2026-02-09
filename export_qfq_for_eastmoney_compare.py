#!/usr/bin/env python3
"""
导出 5 只有差异股票的 DB load_qfq 前复权收盘价，供人工与东方财富对比

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


def main():
    from core.modules.data_manager import DataManager

    data_mgr = DataManager(is_verbose=False)
    data_mgr.initialize()

    print("=" * 60)
    print("DB load_qfq 前复权收盘价（供与东方财富人工对比）")
    print("=" * 60)
    print("东方财富：quote.eastmoney.com -> 股票代码 -> K线 -> 前复权")
    print("")

    for stock_id in STOCKS:
        rows = data_mgr.stock.kline.load_qfq(
            stock_id, term="daily", start_date=START, end_date=END
        )
        if not rows:
            print(f"{stock_id}: 无数据\n")
            continue

        # 日期格式统一为 YYYY-MM-DD 便于东方财富对照
        dated = []
        for r in rows:
            d = r.get("date")
            close = r.get("qfq_close")
            if d and close is not None:
                d_str = str(d).replace("-", "")
                if len(d_str) == 8:
                    dated.append((d_str[:4] + "-" + d_str[4:6] + "-" + d_str[6:8], float(close)))
        dated.sort(key=lambda x: x[0])

        print(f"--- {stock_id} ---")
        print("日期         qfq_close")
        for d, c in dated:
            print(f"{d}   {c:.4f}")
        print()

    print("=" * 60)

    # 同时导出到 CSV
    out_path = os.path.join(os.path.dirname(__file__), "qfq_for_eastmoney_compare.csv")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("stock_id,date,qfq_close\n")
        for stock_id in STOCKS:
            rows = data_mgr.stock.kline.load_qfq(
                stock_id, term="daily", start_date=START, end_date=END
            )
            for r in rows:
                d = r.get("date")
                close = r.get("qfq_close")
                if d and close is not None:
                    d_str = str(d).replace("-", "")
                    if len(d_str) == 8:
                        d_fmt = d_str[:4] + "-" + d_str[4:6] + "-" + d_str[6:8]
                        f.write(f"{stock_id},{d_fmt},{close:.4f}\n")
    print(f"\n已导出 CSV: qfq_for_eastmoney_compare.csv")


if __name__ == "__main__":
    main()
