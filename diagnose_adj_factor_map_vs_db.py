#!/usr/bin/env python3
"""
诊断 adj_factor_event：map/build 阶段 vs save 阶段

直接查 DB，对比：
1. sys_adj_factor_events 表中的 id 格式和样例
2. sys_stock_list 中的 id 格式
3. load_latests 返回的 last_update_map keys（与 build job 时一致）
4. 000903.SZ 是否在 adj_factor_events 表中
5. stock_list 中有多少不在 adj_factor_events（需全量）
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from loguru import logger
from core.modules.data_manager import DataManager
from core.modules.data_source.service.handler_helper import DataSourceHandlerHelper
from userspace.data_source.handlers.adj_factor_event.config import CONFIG
from core.modules.data_source.data_class.config import DataSourceConfig


def main():
    data_manager = DataManager(is_verbose=False)
    data_manager.initialize()
    db = data_manager.db

    print("\n" + "=" * 70)
    print("【1】sys_adj_factor_events 表：id 格式和样例")
    print("=" * 70)

    sql1 = """
        SELECT id, event_date, last_update
        FROM sys_adj_factor_events
        ORDER BY id, event_date DESC
        LIMIT 15
    """
    try:
        rows = db.execute_sync_query(sql1, ())
        if rows:
            # 去重 id 展示
            seen = set()
            for r in rows:
                sid = r.get("id")
                if sid and sid not in seen:
                    seen.add(sid)
                    print(f"  id={repr(sid)}, type={type(sid).__name__}, last_update={r.get('last_update')}")
            print(f"\n  表总行数: SELECT COUNT(*) ...")
        else:
            print("  表为空")
    except Exception as e:
        print(f"  查询失败: {e}")

    sql_count = "SELECT COUNT(*) as cnt FROM sys_adj_factor_events"
    try:
        cnt = db.execute_sync_query(sql_count, ())[0]["cnt"]
        print(f"  表总行数: {cnt}")
    except Exception as e:
        print(f"  count 失败: {e}")

    sql_distinct = "SELECT DISTINCT id FROM sys_adj_factor_events LIMIT 20"
    try:
        ids = [r["id"] for r in db.execute_sync_query(sql_distinct, ())]
        print(f"  去重 id 样例（前20）: {ids}")
    except Exception as e:
        print(f"  distinct 失败: {e}")

    print("\n" + "=" * 70)
    print("【2】000903.SZ 是否在 sys_adj_factor_events 表中？")
    print("=" * 70)

    for test_id in ["000903.SZ", "000903", "002115.SZ"]:
        sql_check = "SELECT id, event_date, last_update FROM sys_adj_factor_events WHERE id = %s LIMIT 3"
        try:
            r = db.execute_sync_query(sql_check, (test_id,))
            if r:
                print(f"  {repr(test_id)}: 存在 {len(r)} 条，样例 last_update={r[0].get('last_update')}")
            else:
                print(f"  {repr(test_id)}: 不存在")
        except Exception as e:
            print(f"  {repr(test_id)}: 查询失败 {e}")

    print("\n" + "=" * 70)
    print("【3】sys_stock_list：id 格式和 000903.SZ")
    print("=" * 70)

    try:
        stocks = db.execute_sync_query(
            "SELECT id, name FROM sys_stock_list WHERE id IN (%s, %s)",
            ("000903.SZ", "002115.SZ"),
        )
        for s in stocks:
            print(f"  id={repr(s.get('id'))}, name={s.get('name')}")
        if not stocks:
            print("  未找到 000903 相关股票")
    except Exception as e:
        print(f"  查询失败: {e}")

    print("\n" + "=" * 70)
    print("【4】框架 compute_last_update_map（与 build job 时一致）")
    print("=" * 70)

    config = DataSourceConfig.from_dict(CONFIG, data_source_key="adj_factor_event")
    latest = data_manager.service.calendar.get_latest_completed_trading_date()
    context = {
        "config": config,
        "data_manager": data_manager,
        "latest_completed_trading_date": latest,
        "dependencies": {"stock_list": data_manager.service.stock.list.load_all()},
    }

    last_update_map = DataSourceHandlerHelper.compute_last_update_map(context)
    print(f"  last_update_map 总数: {len(last_update_map)}")
    sample = list(last_update_map.items())[:5]
    print(f"  样例 keys: {[k for k, _ in sample]}")
    print(f"  000903.SZ in map: {'000903.SZ' in last_update_map}")
    if "000903.SZ" in last_update_map:
        print(f"  000903.SZ value: {last_update_map['000903.SZ']}")
    else:
        print("  000903.SZ 不在 map 中 → 会走「无 last_update 需全量」逻辑")

    print("\n" + "=" * 70)
    print("【5】stock_list vs adj_factor_events：多少股票在表中无记录？")
    print("=" * 70)

    stock_list = data_manager.service.stock.list.load_all()
    stock_ids = {str(s.get("id") or s.get("ts_code") or s) for s in stock_list if s}
    adj_ids = {r["id"] for r in db.execute_sync_query("SELECT DISTINCT id FROM sys_adj_factor_events", ())}

    in_stock_not_in_adj = stock_ids - adj_ids
    in_adj_not_in_stock = adj_ids - stock_ids
    print(f"  stock_list 股票数: {len(stock_ids)}")
    print(f"  adj_factor_events 有记录的股票数: {len(adj_ids)}")
    print(f"  在 stock_list 但 adj 表无记录（需全量）: {len(in_stock_not_in_adj)}")
    print(f"  在 adj 表但 stock_list 无: {len(in_adj_not_in_stock)}")
    if "000903.SZ" in in_stock_not_in_adj:
        print(f"  >>> 000903.SZ 在 stock_list 中，但 adj 表无记录 → 每次都会尝试全量，若 qfq 失败则永不入库")
    if in_stock_not_in_adj:
        print(f"  需全量样例（前10）: {list(in_stock_not_in_adj)[:10]}")

    print("\n" + "=" * 70)
    print("【6】load_latests 原始返回（与 query_latest_date 一致）")
    print("=" * 70)

    adj_model = data_manager.stock.kline._adj_factor_event
    latest_records = adj_model.load_latests(date_field="last_update", group_fields=["id"])
    print(f"  load_latests 返回记录数: {len(latest_records)}")
    for i, r in enumerate(latest_records[:5]):
        print(f"    [{i}] id={repr(r.get('id'))}, last_update={r.get('last_update')}")

    print("\n" + "=" * 70)
    print("诊断完成")
    print("=" * 70)


if __name__ == "__main__":
    main()
