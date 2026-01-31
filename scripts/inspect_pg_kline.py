#!/usr/bin/env python3
"""
连接项目配置的 PostgreSQL，查看 stock_kline 与 sys_stock_kline_monthly 的实际情况。
用法：python -m scripts.inspect_pg_kline 或 python scripts/inspect_pg_kline.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger
from core.modules.data_manager.data_manager import DataManager


def main():
    dm = DataManager(is_verbose=False)
    dm.initialize()
    db = dm.db
    if not db:
        logger.error("未获取到 DatabaseManager")
        return

    def run(q: str, params=None):
        try:
            return db.execute_sync_query(q, params or ())
        except Exception as e:
            logger.error(f"查询失败: {e}\nSQL: {q}")
            return None

    logger.info("========== 1. 旧表 stock_kline 是否存在及行数 ==========")
    r = run("SELECT count(*) AS cnt FROM stock_kline")
    if r is not None:
        logger.info(f"stock_kline 行数: {r[0]['cnt']}")
    else:
        logger.warning("无法查询 stock_kline（表可能不存在）")

    logger.info("========== 2. stock_kline 按 term 分布 ==========")
    r = run("SELECT term, count(*) AS cnt FROM stock_kline GROUP BY term ORDER BY term")
    if r is not None and r:
        for row in r:
            logger.info(f"  term={row.get('term')!r} -> {row.get('cnt')} 行")
    elif r is not None:
        logger.info("  (无数据或表为空)")
    else:
        logger.warning("无法查询 term 分布")

    logger.info("========== 3. stock_kline 表结构（列名） ==========")
    r = run(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_schema = current_schema() AND table_name = 'stock_kline' ORDER BY ordinal_position"
    )
    if r is not None and r:
        for row in r:
            logger.info(f"  {row.get('column_name')} ({row.get('data_type')})")
    else:
        logger.warning("无法查询 stock_kline 列信息")

    logger.info("========== 3b. 行数差异诊断（旧表重复 id+date 会导致新表行数变少） ==========")
    for term_name, term_val in [("monthly", "monthly"), ("weekly", "weekly")]:
        r_total = run("SELECT count(*) AS cnt FROM stock_kline WHERE term = %s", (term_val,))
        r_distinct = run(
            "SELECT count(*) AS cnt FROM (SELECT id, date FROM stock_kline WHERE term = %s GROUP BY id, date) t",
            (term_val,),
        )
        r_new = run(f"SELECT count(*) AS cnt FROM sys_stock_kline_{term_name}")
        if r_total and r_distinct and r_new:
            total = r_total[0]["cnt"]
            distinct = r_distinct[0]["cnt"]
            new_cnt = r_new[0]["cnt"]
            dup = total - distinct
            logger.info(
                f"  term={term_val}: 旧表总行数={total}, 旧表去重(id,date)={distinct}, 重复行={dup}, 新表行数={new_cnt}"
            )
        else:
            logger.warning(f"  term={term_val}: 查询失败")

    logger.info("========== 4. 新表 sys_stock_kline_monthly / weekly 行数 ==========")
    for tbl in ("sys_stock_kline_monthly", "sys_stock_kline_weekly"):
        r = run(f"SELECT count(*) AS cnt FROM {tbl}")
        if r is not None:
            logger.info(f"  {tbl}: {r[0]['cnt']} 行")
        else:
            logger.warning(f"  无法查询 {tbl}")

    logger.info("========== 5. 新表样本行（各取 1 行） ==========")
    for tbl in ("sys_stock_kline_monthly", "sys_stock_kline_weekly"):
        r = run(f"SELECT * FROM {tbl} LIMIT 1")
        if r is not None and r:
            row = r[0]
            logger.info(f"  {tbl} 样本: id={row.get('id')}, date={row.get('date')}, open={row.get('open')}, close={row.get('close')}, volume={row.get('volume')}")
        elif r is not None:
            logger.info(f"  {tbl}: (无数据)")
        else:
            logger.warning(f"  {tbl}: 查询失败")

    logger.info("========== 6. stock_kline 中 term=monthly 的样本 1 行（列名与值） ==========")
    r = run("SELECT * FROM stock_kline WHERE lower(trim(term::text)) = 'monthly' LIMIT 1")
    if r is not None and r:
        row = r[0]
        for k, v in sorted(row.items()):
            logger.info(f"  {k}: {v}")
    elif r is not None:
        logger.info("  (无 term=monthly 的数据)")
    else:
        logger.warning("无法查询样本行")

    logger.info("========== 结束 ==========")


def main_quick():
    """仅查新表行数，少打日志。"""
    dm = DataManager(is_verbose=False)
    dm.initialize()
    db = dm.db
    if not db:
        logger.error("未获取到 DatabaseManager")
        return
    for tbl in ("sys_stock_kline_monthly", "sys_stock_kline_weekly"):
        try:
            r = db.execute_sync_query(f"SELECT count(*) AS cnt FROM {tbl}", ())
            logger.info(f"{tbl}: {r[0]['cnt']} 行")
        except Exception as e:
            logger.warning(f"{tbl}: 查询失败 - {e}")


if __name__ == "__main__":
    main()
