#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
按表备份（基于核心 model.export_data 的 CLI 包装）。

默认行为（不带 --full）：
- 对所有表执行备份；
- 存在时间字段（date / trade_date / event_date）的表，仅备份默认时间窗口（见 DEFAULT_*）；
- 无时间字段的表，仍按全量备份。

全量行为（带 --full）：
- 所有表全量备份。

可选地可指定 --start-date / --end-date 覆盖默认窗口。

清理旧备份目录调用与核心一致的 `DataManager.backup_restore.prune_old_backups`。
"""
import sys
import re
import argparse
import logging
from pathlib import Path
from datetime import date
from typing import Optional, Tuple

# 项目根目录（供 import core）
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.infra.project_context import PathManager

OUT_DIR = PathManager.backup_data()

DATE_FMT = "%Y%m%d"
# 默认窗口：固定 2025 全年（Demo 对外数据窗口）
DEFAULT_START_DATE = "20250101"
DEFAULT_END_DATE = "20251231"
TIME_FIELDS = ("date", "trade_date", "event_date")

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def _default_date_range() -> Tuple[str, str]:
    """默认导出时间窗口（固定 2025 全年）。"""
    return DEFAULT_START_DATE, DEFAULT_END_DATE


def _pick_time_field(model) -> Optional[str]:
    """从模型 schema 中选择时间字段（支持 date / trade_date / event_date）。"""
    schema = getattr(model, "schema", None) or {}
    fields = schema.get("fields", []) if isinstance(schema, dict) else []
    names = {f.get("name") for f in fields if isinstance(f, dict)}
    for candidate in TIME_FIELDS:
        if candidate in names:
            return candidate
    return None


def _condition_for_export(
    *,
    model,
    table_name: str,
    full: bool,
    start_date: str,
    end_date: str,
) -> Tuple[str, tuple]:
    """返回传给 model.export_data 的 condition 与 params。"""
    if full:
        logger.info("开始导出表 %s (全量)", table_name)
        return "1=1", ()

    time_field = _pick_time_field(model)
    if time_field:
        logger.info(
            "开始导出表 %s (按 %s 过滤: %s~%s)",
            table_name,
            time_field,
            start_date,
            end_date,
        )
        cond = f"{time_field} >= %s AND {time_field} <= %s"
        return cond, (start_date, end_date)

    logger.info("开始导出表 %s (无时间列，按全量导出)", table_name)
    return "1=1", ()


def _export_one_model(
    *,
    model,
    table_name: str,
    backup_dir: Path,
    archive_format: str,
    full: bool,
    start_date: str,
    end_date: str,
) -> None:
    condition, params = _condition_for_export(
        model=model,
        table_name=table_name,
        full=full,
        start_date=start_date,
        end_date=end_date,
    )
    paths = model.export_data(
        output_dir=backup_dir,
        archive_format=archive_format,
        condition=condition,
        params=params,
    )
    for p in paths:
        logger.info("导出 %s -> %s", table_name, p.name)


def run_export_all(
    dm,
    *,
    archive_format: str,
    full: bool,
    start_date: str,
    end_date: str,
) -> None:
    """导出所有注册表到 userspace/backup/data/{今日}/all_tables/。"""
    backup_date = date.today().strftime(DATE_FMT)
    backup_dir = OUT_DIR / backup_date / "all_tables"
    backup_dir.mkdir(parents=True, exist_ok=True)

    all_tables = sorted(dm._table_cache.keys())
    logger.info("将导出全部表，共 %d 张", len(all_tables))
    for name in all_tables:
        model = dm.get_table(name)
        if model is None:
            logger.warning("表未注册，跳过: %s", name)
            continue
        _export_one_model(
            model=model,
            table_name=name,
            backup_dir=backup_dir,
            archive_format=archive_format,
            full=full,
            start_date=start_date,
            end_date=end_date,
        )

    logger.info("全部表导出完成，目录: %s", backup_dir)


def run_export(
    dm,
    table_name: str,
    archive_format: str,
    *,
    full: bool,
    start_date: str,
    end_date: str,
) -> None:
    """导出单表到 userspace/backup/data/{今日}/。"""
    if not dm.db:
        raise RuntimeError("DataManager 未初始化或数据库不可用")

    model = dm.get_table(table_name)
    if model is None:
        raise SystemExit(f"表未注册: {table_name}")

    backup_date = date.today().strftime(DATE_FMT)
    backup_dir = OUT_DIR / backup_date
    backup_dir.mkdir(parents=True, exist_ok=True)

    _export_one_model(
        model=model,
        table_name=table_name,
        backup_dir=backup_dir,
        archive_format=archive_format,
        full=full,
        start_date=start_date,
        end_date=end_date,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "按表备份到 userspace/backup/data/（调用核心 model.export_data）。"
            "默认按固定时间窗口备份（当前 2025 全年）；带 --full 时全量备份。"
        )
    )
    parser.add_argument(
        "-t",
        "--table",
        help="单表导出（不传则导出所有表）",
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
        help="在 userspace/backup/data/ 下最多保留的备份日期目录数量，默认 3",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="全量导出（忽略时间窗口）",
    )
    parser.add_argument(
        "--start-date",
        help="窗口起始日期（YYYYMMDD）。默认 20250101",
    )
    parser.add_argument(
        "--end-date",
        help="窗口结束日期（YYYYMMDD）。默认 20251231",
    )
    args = parser.parse_args()

    default_start, default_end = _default_date_range()
    start_date = args.start_date or default_start
    end_date = args.end_date or default_end

    if not re.fullmatch(r"\d{8}", start_date):
        raise SystemExit(f"--start-date 格式错误: {start_date}，应为 YYYYMMDD")
    if not re.fullmatch(r"\d{8}", end_date):
        raise SystemExit(f"--end-date 格式错误: {end_date}，应为 YYYYMMDD")
    if start_date > end_date:
        raise SystemExit(f"日期区间非法: start_date({start_date}) > end_date({end_date})")

    if args.full:
        logger.info("导出模式：全量（忽略时间窗口）")
    else:
        logger.info("导出模式：时间窗口 [%s, %s]", start_date, end_date)

    from core.modules.data_manager import DataManager

    dm = DataManager(is_verbose=False)
    dm.initialize()

    if args.table:
        run_export(
            dm,
            table_name=args.table.strip(),
            archive_format=args.format,
            full=args.full,
            start_date=start_date,
            end_date=end_date,
        )
    else:
        run_export_all(
            dm,
            archive_format=args.format,
            full=args.full,
            start_date=start_date,
            end_date=end_date,
        )

    dm.backup_restore.prune_old_backups(keep=args.keep)


if __name__ == "__main__":
    main()
