#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
按表导出/备份（Demo 数据打包用 CLI）。

默认行为（不带 --full）：
- 对所有表执行导出；
- 存在时间字段（date/trade_date）的表，仅导出默认时间窗口（当前 1 年）；
- 无时间字段的表，仍按全量导出。

全量行为（带 --full）：
- 所有表全量导出。

可选地可指定 --start-date / --end-date 覆盖默认窗口。
"""
import sys
import os
import re
import argparse
import logging
import shutil
from pathlib import Path
from datetime import date
from typing import List, Optional

# 项目根目录
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
os.chdir(_REPO_ROOT)

from core.utils.io import file_io, csv_io

# 输出目录：backup/data
OUT_DIR = _REPO_ROOT / "backup" / "data"

DATE_FMT = "%Y%m%d"
# 默认窗口：固定 2025 全年（Demo 对外数据窗口）
DEFAULT_START_DATE = "20250101"
DEFAULT_END_DATE = "20251231"
TIME_FIELDS = ("date", "trade_date")

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def _default_date_range() -> tuple[str, str]:
    """默认导出时间窗口（固定 2025 全年）。"""
    return DEFAULT_START_DATE, DEFAULT_END_DATE


def _pick_time_field(model) -> Optional[str]:
    """
    从模型 schema 中选择时间字段（当前支持 date / trade_date）。
    """
    schema = getattr(model, "schema", None) or {}
    fields = schema.get("fields", []) if isinstance(schema, dict) else []
    names = {f.get("name") for f in fields if isinstance(f, dict)}
    for candidate in TIME_FIELDS:
        if candidate in names:
            return candidate
    return None


def _export_adj_factor_events_for_window(
    *,
    model,
    table_name: str,
    backup_dir: Path,
    archive_format: str,
    start_date: str,
    end_date: str,
) -> None:
    """
    sys_adj_factor_events 专用导出：
    - 导出窗口内 event_date ∈ [start_date, end_date] 的事件；
    - 对每个股票补一条 start_date 锚点事件：
      1) 优先取 <= start_date 的最近一条；
      2) 若不存在，取 > start_date 的最早一条；
      3) 若该股票无任何事件，则不补（该股票只能裸价）。
    仅影响导出内容，不写回数据库。
    """
    db = getattr(model, "db", None)
    if db is None:
        raise RuntimeError(f"{table_name} model 不可用：缺少 db 连接")

    # 以 K 线窗口内出现的股票为基准补锚点（保证 demo 用到的股票都可复权）
    stock_rows = db.execute_sync_query(
        """
        SELECT DISTINCT id
        FROM sys_stock_klines
        WHERE date >= %s AND date <= %s
        ORDER BY id ASC
        """,
        (start_date, end_date),
    )
    stock_ids = [r.get("id") for r in stock_rows or [] if r.get("id")]

    # 窗口内原始事件
    in_range_rows: List[dict] = []
    if stock_ids:
        placeholders = ",".join(["%s"] * len(stock_ids))
        in_range_rows = db.execute_sync_query(
            f"""
            SELECT id, event_date, factor, qfq_diff, last_update
            FROM {table_name}
            WHERE id IN ({placeholders})
              AND event_date >= %s
              AND event_date <= %s
            ORDER BY id ASC, event_date ASC
            """,
            tuple(stock_ids) + (start_date, end_date),
        )

    by_pk: dict[tuple[str, str], dict] = {}
    for row in in_range_rows or []:
        sid = row.get("id")
        ed = row.get("event_date")
        if not sid or not ed:
            continue
        by_pk[(sid, str(ed))] = dict(row)

    # 每个股票补 start_date 锚点（若窗口内已存在该 pk 则不覆盖）
    for sid in stock_ids:
        # 1) <= start_date 最近
        prev = db.execute_sync_query(
            f"""
            SELECT id, event_date, factor, qfq_diff, last_update
            FROM {table_name}
            WHERE id = %s AND event_date <= %s
            ORDER BY event_date DESC
            LIMIT 1
            """,
            (sid, start_date),
        )
        anchor = prev[0] if prev else None

        # 2) 不存在则 > start_date 最早
        if not anchor:
            nxt = db.execute_sync_query(
                f"""
                SELECT id, event_date, factor, qfq_diff, last_update
                FROM {table_name}
                WHERE id = %s AND event_date > %s
                ORDER BY event_date ASC
                LIMIT 1
                """,
                (sid, start_date),
            )
            anchor = nxt[0] if nxt else None

        # 3) 从未有事件，不补（该股票只能裸价）
        if not anchor:
            continue

        k = (sid, start_date)
        if k not in by_pk:
            by_pk[k] = {
                "id": sid,
                "event_date": start_date,
                "factor": anchor.get("factor"),
                "qfq_diff": anchor.get("qfq_diff"),
                "last_update": anchor.get("last_update"),
            }

    rows = sorted(by_pk.values(), key=lambda r: (str(r.get("id", "")), str(r.get("event_date", ""))))
    csv_bytes = csv_io.dicts_to_csv_bytes(rows)
    archive_path = file_io.write_archive(
        backup_dir,
        archive_name=table_name,
        files={f"{table_name}.csv": csv_bytes},
        format="tar.gz" if archive_format == "tar.gz" else "zip",
    )
    logger.info(
        "导出 %s（窗口+起点锚点补齐） -> %s (行数=%d, 股票数=%d)",
        table_name,
        archive_path.name,
        len(rows),
        len(stock_ids),
    )


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
    """
    导出单表：
    - full=True: 全量
    - full=False: 若有时间列按窗口过滤，否则全量
    """
    # 复权事件表特判：窗口导出 + 起点锚点补齐
    if (not full) and table_name == "sys_adj_factor_events":
        _export_adj_factor_events_for_window(
            model=model,
            table_name=table_name,
            backup_dir=backup_dir,
            archive_format=archive_format,
            start_date=start_date,
            end_date=end_date,
        )
        return

    time_field = _pick_time_field(model)
    if full:
        logger.info("开始导出表 %s (全量)", table_name)
        paths = model.export_data(
            output_dir=backup_dir,
            archive_format=archive_format,
        )
    elif time_field:
        condition = f"{time_field} >= %s AND {time_field} <= %s"
        params = (start_date, end_date)
        logger.info(
            "开始导出表 %s (按 %s 过滤: %s~%s)",
            table_name,
            time_field,
            start_date,
            end_date,
        )
        paths = model.export_data(
            output_dir=backup_dir,
            archive_format=archive_format,
            condition=condition,
            params=params,
        )
    else:
        logger.info("开始导出表 %s (无时间列，按全量导出)", table_name)
        paths = model.export_data(
            output_dir=backup_dir,
            archive_format=archive_format,
        )

    for p in paths:
        logger.info("导出 %s -> %s", table_name, p.name)


def run_export_all(
    *,
    archive_format: str,
    full: bool,
    start_date: str,
    end_date: str,
) -> None:
    """
    导出所有注册表。
    """
    from core.modules.data_manager import DataManager

    dm = DataManager(is_verbose=False)
    dm.initialize()

    backup_date = date.today().strftime(DATE_FMT)
    backup_dir = OUT_DIR / backup_date / "all_tables"
    backup_dir.mkdir(parents=True, exist_ok=True)

    # DataManager 内部使用 _table_cache 缓存所有注册表名
    try:
        all_tables = sorted(dm._table_cache.keys())
    except AttributeError:
        raise SystemExit("DataManager 不暴露 tables 属性，请检查实现或改用 _table_cache")

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
    table_name: str,
    archive_format: str,
    *,
    full: bool,
    start_date: str,
    end_date: str,
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

    _export_one_model(
        model=model,
        table_name=table_name,
        backup_dir=backup_dir,
        archive_format=archive_format,
        full=full,
        start_date=start_date,
        end_date=end_date,
    )


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
        description=(
            "按表导出/备份到 backup/data/。默认按固定时间窗口导出（当前 2025 全年）；"
            "带 --full 时全量导出。"
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
        help="在 backup/data/ 下最多保留的备份日期目录数量，默认 3",
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

    if args.table:
        run_export(
            table_name=args.table.strip(),
            archive_format=args.format,
            full=args.full,
            start_date=start_date,
            end_date=end_date,
        )
    else:
        run_export_all(
            archive_format=args.format,
            full=args.full,
            start_date=start_date,
            end_date=end_date,
        )
    prune_old_backups(args.keep)


if __name__ == "__main__":
    main()
