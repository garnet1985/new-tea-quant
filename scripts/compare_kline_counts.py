#!/usr/bin/env python3
"""
对比 stock_kline 与 sys_stock_klines 的记录总数（及按 term 分布）。

不跑迁移，只查 count(*) 并打印。用于快速核对两张表是否一致。

使用：
    python scripts/compare_kline_counts.py
    或从项目根目录：python -m scripts.compare_kline_counts
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.modules.data_manager.data_manager import DataManager


def count_table(dm, table, where=None, params=()):
    if not dm.db.is_table_exists(table):
        return -1
    try:
        if where:
            q = f"SELECT count(*) AS cnt FROM {table} WHERE {where}"
            rows = dm.db.execute_sync_query(q, params)
        else:
            rows = dm.db.execute_sync_query(f"SELECT count(*) AS cnt FROM {table}", ())
        if rows and rows[0].get("cnt") is not None:
            return int(rows[0]["cnt"])
        return 0
    except Exception as e:
        print(f"  查询 {table} 失败: {e}")
        return -1


def main():
    print("连接数据库...")
    dm = DataManager(is_verbose=False)
    dm.initialize()

    old_table = "stock_kline"
    new_table = "sys_stock_klines"

    # 全表总数
    old_total = count_table(dm, old_table)
    new_total = count_table(dm, new_table)

    print()
    print("========== 总行数 ==========")
    print(f"  {old_table}:         {old_total:,}" if old_total >= 0 else f"  {old_table}:         表不存在或查询失败")
    print(f"  {new_table}:  {new_total:,}" if new_total >= 0 else f"  {new_table}:  表不存在或查询失败")

    if old_total >= 0 and new_total >= 0:
        diff = new_total - old_total
        print(f"  差值 (新 - 旧):    {diff:+,}")
        if diff == 0:
            print("  结论: 数量一致")
        elif diff > 0:
            print("  结论: 新表记录更多")
        else:
            print("  结论: 旧表记录更多")

    # 按 term 分布
    print()
    print("========== 按 term 分布 ==========")
    for term in ("daily", "weekly", "monthly"):
        old_c = count_table(dm, old_table, "term = %s", (term,))
        new_c = count_table(dm, new_table, "term = %s", (term,))
        old_s = f"{old_c:,}" if old_c >= 0 else "N/A"
        new_s = f"{new_c:,}" if new_c >= 0 else "N/A"
        diff_s = ""
        if old_c >= 0 and new_c >= 0:
            d = new_c - old_c
            diff_s = f"  (差 {d:+,})"
        print(f"  term={term}:  旧表 {old_s}  新表 {new_s}{diff_s}")

    print()


if __name__ == "__main__":
    main()
