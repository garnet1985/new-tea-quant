#!/usr/bin/env python3
"""
创建系统表并完成表发现/注册

执行顺序：
1. 初始化 DatabaseManager（连接数据库）
2. 根据 core/tables 下所有 schema.py 执行 CREATE TABLE（SchemaManager.create_all_tables）
3. 递归发现 core/tables、userspace/tables 下的 schema.py，对每个目录调用 register_table，注册 Model 到 DataManager
4. 若 sys_index_list 表为空，则从 core/tables/index/index_list/data.json 写入初始值

运行后所有 sys_* 表已建好，且 get_table("sys_xxx") 可用，便于后续数据迁移脚本使用。

使用：
    python scripts/create_sys_tables.py
    或从项目根目录：python -m scripts.create_sys_tables
"""
import sys
import os
import json

# 项目根目录加入 path（与 start-cli.py 一致）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
from loguru import logger
from core.modules.data_manager.data_manager import DataManager


def _seed_sys_index_list_if_empty(dm: DataManager) -> None:
    """若 sys_index_list 表存在且为空，从 core/tables/index/index_list/data.json 写入初始值。"""
    model = dm.get_table("sys_index_list")
    if not model:
        return
    if not dm.db.is_table_exists("sys_index_list"):
        return
    try:
        existing = dm.db.execute_sync_query("SELECT count(*) AS cnt FROM sys_index_list", ())
        if existing and existing[0].get("cnt", 0) > 0:
            return
    except Exception:
        return
    data_path = Path(__file__).resolve().parent.parent / "core" / "tables" / "index" / "index_list" / "data.json"
    if not data_path.is_file():
        logger.warning(f"未找到 sys_index_list 初始值文件: {data_path}")
        return
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            rows = json.load(f)
        if not rows:
            return
        n = model.replace(rows, unique_keys=["id"], use_batch=True)
        logger.info(f"✅ sys_index_list 已写入初始值 {n} 条（来自 data.json）")
    except Exception as e:
        logger.warning(f"写入 sys_index_list 初始值失败: {e}")


def main():
    logger.info("🔧 创建系统表并完成表发现/注册...")
    dm = DataManager(is_verbose=True)
    dm.initialize()
    tables = sorted(dm._table_cache.keys())
    logger.info(f"✅ 系统表已创建并注册，共 {len(tables)} 个表")
    for name in tables:
        logger.info(f"   - {name}")
    _seed_sys_index_list_if_empty(dm)
    logger.info("可执行数据迁移脚本，使用 data_manager.get_table('sys_xxx') 写入新表。")


if __name__ == "__main__":
    main()
