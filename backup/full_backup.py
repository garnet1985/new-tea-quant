#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
整库全量备份（按表）：

- 复用 backup/export_table.py 的导出逻辑和路径约定
- 对所有已配置的系统表做「全表」导出：
  - 有日期列的表：使用极宽的日期区间（19000101 ~ 21001231）
  - 无日期列的表：直接全表导出
- 额外包含 sys_cache / sys_meta_info，方便完整快照恢复

用法（在项目根目录执行）：
    python backup/full_backup.py
    python backup/full_backup.py --format zip
    python backup/full_backup.py --keep 5
"""

import sys
from typing import List

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import argparse  # noqa: E402
import logging  # noqa: E402

from backup.export_table import TABLE_DATE_CONFIG, run_export, prune_old_backups  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


# 需要按时间切块备份的大表（值为分块粒度，目前支持 'year'）
CHUNKED_DATE_TABLES = {
    "sys_stock_indicators": "year",
}


def _parse_yyyymmdd(s: str):
    from datetime import datetime

    return datetime.strptime(s, "%Y%m%d").date()


def _format_yyyymmdd(d) -> str:
    return d.strftime("%Y%m%d")


def _iter_year_chunks(start_yyyymmdd: str, end_yyyymmdd: str):
    """
    按整年切分区间：[YYYY0101, YYYY1231]，最后一段与 end_yyyymmdd 对齐。
    """
    start = _parse_yyyymmdd(start_yyyymmdd)
    end = _parse_yyyymmdd(end_yyyymmdd)

    from datetime import date, timedelta

    cur_start = date(start.year, start.month, start.day)
    one_day = timedelta(days=1)

    while cur_start <= end:
        # 当前块的理论结束日：当年 12 月 31 日
        year_end = date(cur_start.year, 12, 31)
        cur_end = min(year_end, end)
        yield _format_yyyymmdd(cur_start), _format_yyyymmdd(cur_end)
        cur_start = cur_end + one_day


def _full_backup_tables() -> List[str]:
    """
    返回需要做全量备份的表列表。

    - 以 TABLE_DATE_CONFIG 中的系统表为主
    - 额外包含 sys_cache / sys_meta_info 方便完整快照
    """
    base_tables = set(TABLE_DATE_CONFIG.keys())
    extra = {"sys_cache", "sys_meta_info"}
    all_tables = sorted(base_tables | extra)
    return all_tables


def run_full_backup(archive_format: str, keep: int) -> None:
    """
    对所有目标表执行一次全量导出。
    """
    tables = _full_backup_tables()
    logger.info("开始全量备份，共 %d 张表", len(tables))

    for table in tables:
        date_cfg = TABLE_DATE_CONFIG.get(table)

        # 无日期列：不传时间，全表导出（单文件，不带时间范围）
        if date_cfg is None:
            logger.info("全量备份表: %s", table)
            run_export(
                table_name=table,
                start=None,
                end=None,
                duration=None,
                archive_format=archive_format,
                is_full=True,
            )
            continue

        # 大表：按年切块导出，避免一次性拉取过大数据
        if CHUNKED_DATE_TABLES.get(table) == "year":
            # 为该表构造“真实有数据”的年份范围，用于主进度
            from core.modules.data_manager import DataManager  # 延迟导入避免循环依赖

            dm = DataManager(is_verbose=False)
            dm.initialize()
            db = dm.db
            if not db:
                raise RuntimeError("DataManager 未初始化或数据库不可用")

            # 根据 TABLE_DATE_CONFIG 找到日期列
            date_col, kind = date_cfg

            # 使用 DataManager 获取物理表名，避免 schema/search_path 问题
            try:
                physical_table = dm.get_physical_table_name(table)
            except Exception:
                physical_table = table

            # 查询该表的最小/最大“日期或季度”
            with db.get_sync_cursor() as cursor:
                cursor.execute(
                    f"SELECT MIN({date_col}) AS min_v, MAX({date_col}) AS max_v FROM {physical_table}"
                )
                row = cursor.fetchone()

            min_v = row.get("min_v") if row else None
            max_v = row.get("max_v") if row else None

            if not min_v or not max_v:
                logger.info("表 %s 无数据，跳过年度切块备份。", table)
                continue

            # 统一转换为年份区间
            def _year_from_yyyymmdd(v) -> int:
                s = str(v)
                return int(s[:4])

            def _year_from_quarter(v) -> int:
                s = str(v)
                return int(s[:4])

            if kind == "yyyymmdd":
                min_year = _year_from_yyyymmdd(min_v)
                max_year = _year_from_yyyymmdd(max_v)
            else:  # quarter
                min_year = _year_from_quarter(min_v)
                max_year = _year_from_quarter(max_v)

            start_yyyymmdd = f"{min_year}0101"
            end_yyyymmdd = f"{max_year}1231"

            year_chunks = list(_iter_year_chunks(start_yyyymmdd, end_yyyymmdd))
            total_years = len(year_chunks)

            for idx, (start, end) in enumerate(year_chunks, start=1):
                percent = idx * 100.0 / total_years
                logger.info(
                    "全量备份表: %s 年度进度 %d/%d (%.1f%%), 区间 %s ~ %s",
                    table,
                    idx,
                    total_years,
                    percent,
                    start,
                    end,
                )
                run_export(
                    table_name=table,
                    start=start,
                    end=end,
                    duration=None,
                    archive_format=archive_format,
                    is_full=False,
                )
        else:
            # 普通有日期列的表：直接做全表导出（单文件，不带时间范围）
            logger.info("全量备份表: %s", table)
            run_export(
                table_name=table,
                start=None,
                end=None,
                duration=None,
                archive_format=archive_format,
                is_full=True,
            )

    # 统一做一次旧备份目录清理
    prune_old_backups(keep)
    logger.info("全量备份完成。")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="整库全量备份（按表导出到 backup/data/）"
    )
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
    args = parser.parse_args()

    run_full_backup(archive_format=args.format, keep=args.keep)


if __name__ == "__main__":
    main()

