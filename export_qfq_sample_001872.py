#!/usr/bin/env python3
"""
导出 001872.SZ 的 qfq 前复权日线收盘价样本

时间段：
  - 2024年7月 ~ 2024年8月
  - 2025年6月 ~ 2025年7月
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    from core.modules.data_manager import DataManager

    data_mgr = DataManager(is_verbose=False)
    data_mgr.initialize()

    stock_id = "001872.SZ"

    periods = [
        ("2024年7月~8月", "20240701", "20240831"),
        ("2025年6月~7月", "20250601", "20250731"),
    ]

    for label, start_ymd, end_ymd in periods:
        print(f"\n{'='*50}")
        print(f"001872.SZ 前复权收盘价 (qfq_close) - {label}")
        print(f"  日期范围: {start_ymd} ~ {end_ymd}")
        print(f"{'='*50}")
        print(f"{'日期':<12} {'qfq_close':>10}")
        print("-" * 24)

        try:
            rows = data_mgr.stock.kline.load_qfq(
                stock_id, term="daily", start_date=start_ymd, end_date=end_ymd
            )
        except Exception as e:
            print(f"  加载失败: {e}")
            continue

        if not rows:
            print("  (无数据)")
            continue

        for r in rows:
            d = r.get("date")
            d_str = str(d).replace("-", "") if d else ""
            qfq = r.get("qfq_close", "")
            if qfq is not None:
                print(f"{d_str:<12} {float(qfq):>10.4f}")
            else:
                print(f"{d_str:<12} {'N/A':>10}")

    print()


if __name__ == "__main__":
    main()
