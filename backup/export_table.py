#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
按表导出/备份（测试用 CLI）：

- 直接调用 DbBaseModel.export_data，将单表数据导出到 backup/data/{today}/ 下
- 提供若干批量导出测试入口：
  - 单表全量导出
  - stock klines 在 2023-01-01 ~ 2025-12-31 区间
  - stock indicators 在 2023-01-01 ~ 2025-12-31 区间
  - 其余表全量导出

用法（在项目根目录执行）：
    # 单表全量导出
    python backup/export_table.py -t sys_corporate_finance

    # 批次一：stock klines 2023-01-01 ~ 2025-12-31
    python backup/export_table.py --batch-klines-3y

    # 批次二：stock indicators 2023-01-01 ~ 2025-12-31
    python backup/export_table.py --batch-ind-3y

    # 批次三：其余表全量导出
    python backup/export_table.py --batch-others-full
"""
import sys
import os
import re
import argparse
import logging
import shutil
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import List

# 项目根目录
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
os.chdir(_REPO_ROOT)

from core.utils.io import file_io

# 输出目录：backup/data
OUT_DIR = _REPO_ROOT / "backup" / "data"

DATE_FMT = "%Y%m%d"

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def run_test_stock_indicators_3y(archive_format: str) -> None:
    """
    测试导出：导出 sys_stock_indicators 在 2023-01-01 ~ 2025-12-31 区间内的数据。

    仅用于开发/验证用，后续会被更通用的业务导出能力替代。
    """
    from core.modules.data_manager import DataManager

    dm = DataManager(is_verbose=False)
    dm.initialize()

    model = dm.get_table("sys_stock_indicators")
    if model is None:
        raise SystemExit("表未注册: sys_stock_indicators")

    # 区间：2023-01-01 ~ 2025-12-31
    start = "20230101"
    end = "20251231"
    condition = "date >= %s AND date <= %s"
    params = (start, end)

    # 备份目录（与 export_data 的全量导出保持一致）
    backup_date = date.today().strftime(DATE_FMT)
    backup_dir = OUT_DIR / backup_date
    backup_dir.mkdir(parents=True, exist_ok=True)

    # 走 DbBaseModel.export_data（条件导出 + 自动分批）
    paths = model.export_data(
        output_dir=backup_dir,
        archive_format=archive_format,
        condition=condition,
        params=params,
    )
    for p in paths:
        logger.info(
            "测试导出 sys_stock_indicators 区间 [%s, %s] -> %s",
            start,
            end,
            p.name,
        )


def run_batch_stock_klines_3y(archive_format: str) -> None:
    """
    批次一：导出 stock klines 在 2023-01-01 ~ 2025-12-31 区间内的数据。
    目前仅包含 sys_stock_klines，一旦有更多 kline 表可在此处扩展列表。
    """
    from core.modules.data_manager import DataManager

    dm = DataManager(is_verbose=False)
    dm.initialize()

    backup_date = date.today().strftime(DATE_FMT)
    backup_dir = OUT_DIR / backup_date / "batch1_stock_klines"
    backup_dir.mkdir(parents=True, exist_ok=True)

    start = "20230101"
    end = "20251231"
    condition = "date >= %s AND date <= %s"
    params = (start, end)

    table_names = ["sys_stock_klines"]

    logger.info("批次一：stock klines 表: %s", table_names)

    for name in table_names:
        model = dm.get_table(name)
        if model is None:
            logger.warning("表未注册，跳过: %s", name)
            continue
        logger.info("开始导出表 %s (2023-01-01 ~ 2025-12-31)", name)
        paths = model.export_data(
            output_dir=backup_dir,
            archive_format=archive_format,
            condition=condition,
            params=params,
        )
        for p in paths:
            logger.info("导出 %s -> %s", name, p.name)

    logger.info("批次一完成，目录: %s", backup_dir)


def run_batch_stock_indicators_3y(archive_format: str) -> None:
    """
    批次二：导出 stock indicators 在 2023-01-01 ~ 2025-12-31 区间内的数据。
    当前仅包含 sys_stock_indicators。
    """
    run_test_stock_indicators_3y(archive_format=archive_format)


def run_batch_others_full(archive_format: str) -> None:
    """
    批次三：导出除 kline / indicators 外的所有表（全量，不按日期过滤）。
    """
    from core.modules.data_manager import DataManager

    dm = DataManager(is_verbose=False)
    dm.initialize()

    backup_date = date.today().strftime(DATE_FMT)
    backup_dir = OUT_DIR / backup_date / "batch3_others_full"
    backup_dir.mkdir(parents=True, exist_ok=True)

    # DataManager 内部使用 _table_cache 缓存所有注册表名
    try:
        all_tables = sorted(dm._table_cache.keys())
    except AttributeError:
        raise SystemExit("DataManager 不暴露 tables 属性，请检查实现或改用 _table_cache")

    handled = {"sys_stock_klines", "sys_stock_indicators"}
    other_tables = [name for name in all_tables if name not in handled]

    logger.info("批次三：其余表（全量导出）: %s", other_tables)

    for name in other_tables:
        model = dm.get_table(name)
        if model is None:
            logger.warning("表未注册，跳过: %s", name)
            continue
        logger.info("开始导出表 %s (全量)", name)
        paths = model.export_data(
            output_dir=backup_dir,
            archive_format=archive_format,
        )
        for p in paths:
            logger.info("导出 %s -> %s", name, p.name)

    logger.info("批次三完成，目录: %s", backup_dir)


def run_export(
    table_name: str,
    archive_format: str,
) -> None:
    from core.modules.data_manager import DataManager

    dm = DataManager(is_verbose=False)
    dm.initialize()
    db = dm.db
    if not db:
        raise RuntimeError("DataManager 未初始化或数据库不可用")

    model = dm.get_table(table_name)
    if model is None:
        raise SystemExit(f"表未注册: {table_name}")

    # 统一确定备份日期目录
    backup_date = date.today().strftime(DATE_FMT)
    backup_dir = OUT_DIR / backup_date
    backup_dir.mkdir(parents=True, exist_ok=True)

    # 直接走 DbBaseModel.export_data（整表导出，内部可自动分批）
    paths = model.export_data(
        output_dir=backup_dir,
        archive_format=archive_format,
    )
    for p in paths:
        logger.info("导出 %s -> %s", table_name, p.name)


def prune_old_backups(keep: int) -> None:
    """
    在 backup/data/ 下按日期目录名（YYYYMMDD）保留最新 keep 个，其余整目录删除。
    """
    if keep <= 0 or not OUT_DIR.exists():
        return

    candidates: List[Path] = []
    for p in OUT_DIR.iterdir():
        if p.is_dir() and re.fullmatch(r"\d{8}", p.name):
            candidates.append(p)

    if len(candidates) <= keep:
        return

    # 按目录名倒序（新日期在前）
    candidates.sort(key=lambda p: p.name, reverse=True)
    to_delete = candidates[keep:]
    if not to_delete:
        return

    logger.info(
        "清理旧备份目录，只保留最近 %d 个：删除 %s",
        keep,
        ", ".join(p.name for p in to_delete),
    )
    for p in to_delete:
        try:
            shutil.rmtree(p)
        except Exception as e:
            logger.warning("删除备份目录失败 %s: %s", p, e)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="按表导出/备份到 backup/data/（export_data 测试 CLI）"
    )
    parser.add_argument("-t", "--table", help="表名，如 sys_corporate_finance（单表导出时使用）")
    parser.add_argument(
        "--format",
        choices=["tar.gz", "zip"],
        default="tar.gz",
        help="打包格式，默认 tar.gz",
    )
    parser.add_argument(
        "--keep",
        type=int,
        default=3,
        help="在 backup/data/ 下最多保留的备份日期目录数量，默认 3",
    )
    parser.add_argument(
        "--batch-klines-3y",
        action="store_true",
        help="批次一：导出 stock klines 在 2023-01-01 ~ 2025-12-31 区间的数据",
    )
    parser.add_argument(
        "--batch-ind-3y",
        action="store_true",
        help="批次二：导出 stock indicators 在 2023-01-01 ~ 2025-12-31 区间的数据",
    )
    parser.add_argument(
        "--batch-others-full",
        action="store_true",
        help="批次三：导出除 kline / indicators 外的所有表（全量）",
    )
    args = parser.parse_args()

    # 批量模式优先
    if args.batch_klines_3y:
        run_batch_stock_klines_3y(archive_format=args.format)
    elif args.batch_ind_3y:
        run_batch_stock_indicators_3y(archive_format=args.format)
    elif args.batch_others_full:
        run_batch_others_full(archive_format=args.format)
    else:
        if not args.table:
            raise SystemExit("单表导出需要指定 -t/--table")
        table_name = args.table.strip()
        run_export(
            table_name=table_name,
            archive_format=args.format,
        )
    prune_old_backups(args.keep)


if __name__ == "__main__":
    main()
