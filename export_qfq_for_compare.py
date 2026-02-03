#!/usr/bin/env python3
"""
导出 load_qfq 前复权收盘价到 CSV，便于与东方财富网站对比验证。

从 DB 随机选几只股票、一个时间段，导出 qfq_close，用户可去东方财富核对。
"""
import sys
import os
import csv
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    from core.modules.data_manager import DataManager
    from core.infra.db import DatabaseManager

    data_mgr = DataManager(is_verbose=False)
    data_mgr.initialize()
    db = DatabaseManager.get_default()

    # 时间段：2024-06-10 ~ 2024-06-20（含平安银行 6/14 除权除息）
    start_ymd = "20240610"
    end_ymd = "20240620"

    # 从 DB 取该时间段内有数据的股票，随机选 5 只
    sql = """
        SELECT DISTINCT id FROM sys_stock_klines
        WHERE term = 'daily' AND date >= %s AND date <= %s
        ORDER BY id
    """
    try:
        rows = db.execute_sync_query(sql, (start_ymd, end_ymd))
        stock_ids = [r["id"] for r in rows] if rows else []
    except Exception as e:
        print(f"查询股票失败: {e}")
        stock_ids = []

    if not stock_ids:
        # 若该时间段无数据，尝试全表取几只
        sql2 = "SELECT DISTINCT id FROM sys_stock_klines WHERE term = 'daily' LIMIT 20"
        try:
            rows = db.execute_sync_query(sql2, ())
            stock_ids = [r["id"] for r in rows] if rows else []
        except Exception:
            stock_ids = ["000001.SZ", "600000.SH", "000002.SZ"]

    stocks = random.sample(stock_ids, min(5, len(stock_ids)))

    # 导出 CSV
    out_path = os.path.join(os.path.dirname(__file__), "qfq_compare_export.csv")
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["stock_id", "date", "close", "qfq_close", "东方财富链接"])
        for stock_id in stocks:
            try:
                rows = data_mgr.stock.kline.load_qfq(
                    stock_id, term="daily", start_date=start_ymd, end_date=end_ymd
                )
            except Exception as e:
                print(f"  {stock_id}: 加载失败 {e}")
                continue
            if not rows:
                continue
            # 东方财富链接：000001.SZ -> sz000001
            code = stock_id.replace(".SZ", "").replace(".SH", "")
            market = "sz" if ".SZ" in stock_id else "sh"
            em_url = f"https://quote.eastmoney.com/{market}{code}.html"
            for r in rows:
                d = r.get("date")
                d_str = str(d).replace("-", "") if d else ""
                close = r.get("close", "")
                qfq = r.get("qfq_close", "")
                w.writerow([stock_id, d_str, close, qfq, em_url])

    print(f"已导出: {out_path}")
    print(f"股票: {stocks}")
    print(f"时间段: {start_ymd} ~ {end_ymd}")
    print("请用 Excel 打开 CSV，到东方财富对应股票日 K 前复权核对 qfq_close。")


if __name__ == "__main__":
    main()
