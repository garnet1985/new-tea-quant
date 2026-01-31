#!/usr/bin/env python3
"""
将 sys_stock_list 表结构迁移为新 schema：删除 industry_id、market_id、board_id 三列；
并为已有维度表 sys_industries、sys_boards、sys_markets 补上 id 自增（序列 + DEFAULT）。

新 schema 下行业/板块/市场由定义表 + 映射表维护，sys_stock_list 仅保留 id、name、is_active、last_update。
维度表 id 在 schema 中已声明 autoIncrement，新建表会直接是 SERIAL；已存在的表需本脚本补序列与 DEFAULT。

执行顺序建议：
1. 若库中 sys_stock_list 仍有上述三列且需保留维度关系：先执行
   python scripts/seed_dimension_tables_from_stock_list.py
   用现有数据填充 sys_industries、sys_boards、sys_markets 及三张映射表。
2. 再执行本脚本：先为维度表补 id 自增，再删除 sys_stock_list 的三列。

使用：
    python scripts/migrate_stock_list_schema.py
    python -m scripts.migrate_stock_list_schema
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger
from core.modules.data_manager.data_manager import DataManager


def _ensure_dimension_id_sequences(db):
    """为已有维度表补 id 自增：创建序列、设置 DEFAULT nextval、setval(MAX(id))。新建表由 schema 的 SERIAL 处理。"""
    for table_name in ("sys_industries", "sys_boards", "sys_markets"):
        seq_name = f"{table_name}_id_seq"
        with db.get_connection() as conn:
            try:
                conn.execute(f"CREATE SEQUENCE IF NOT EXISTS {seq_name}")
                conn.execute(f"ALTER TABLE {table_name} ALTER COLUMN id SET DEFAULT nextval('{seq_name}')")
                conn.execute(f"SELECT setval('{seq_name}', (SELECT COALESCE(MAX(id), 0) FROM {table_name}))")
                logger.info(f"已为 {table_name}.id 设置自增序列 {seq_name}")
            except Exception as e:
                logger.warning(f"为 {table_name} 设置 id 自增时失败（表可能尚未创建）: {e}")


def _column_exists(db, table_name: str, column_name: str) -> bool:
    """检查表中是否存在指定列（PostgreSQL information_schema）。"""
    try:
        rows = db.execute_sync_query(
            """
            SELECT 1 FROM information_schema.columns
            WHERE table_name = %s AND column_name = %s
            """,
            (table_name, column_name),
        )
        return bool(rows and len(rows) > 0)
    except Exception as e:
        logger.warning(f"检查列是否存在失败: {e}")
        return False


def main():
    dm = DataManager(is_verbose=True)
    dm.initialize()
    db = dm.db

    _ensure_dimension_id_sequences(db)

    table_name = "sys_stock_list"
    columns_to_drop = ["industry_id", "market_id", "board_id"]
    existing = [c for c in columns_to_drop if _column_exists(db, table_name, c)]
    if not existing:
        logger.info(f"表 {table_name} 中已无 {columns_to_drop} 列，无需迁移。")
        return

    # PostgreSQL: 每个 DROP COLUMN 单独一条语句更稳妥（IF EXISTS 避免重复执行报错）
    with db.get_connection() as conn:
        for col in existing:
            try:
                sql = f"ALTER TABLE {table_name} DROP COLUMN IF EXISTS {col}"
                conn.execute(sql)
                logger.info(f"已删除列: {table_name}.{col}")
            except Exception as e:
                logger.error(f"删除列 {table_name}.{col} 失败: {e}")
                raise

    logger.info("sys_stock_list 表结构迁移完成。")


if __name__ == "__main__":
    main()
