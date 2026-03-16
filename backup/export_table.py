#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
按表导出/备份：单表导出为 CSV 并打包，输出到 backup/data/。

日期格式 YYYYMMDD。duration 支持 d（日）、m（月）、y（年），如 30d、3m、2y。
区间优先级：-s 与 -e 同时给出则用区间；否则 -s + -d 正推；否则 -e + -d 倒推。
无日期列的表：不传日期参数时全表导出，日期参数无效。

用法（在项目根目录执行）：
    python backup/export_table.py -t sys_corporate_finance -s 20230101 -e 20251231
    python backup/export_table.py -t sys_corporate_finance -s 20230101 -d 1095d
    python backup/export_table.py -t sys_corporate_finance -e 20251231 -d 3y
    python backup/export_table.py -t sys_stock_list
    python backup/export_table.py -t sys_corporate_finance -s 20230101 -e 20251231 --format zip
"""
import sys
import os
import re
import csv
import io
import zipfile
import tarfile
import argparse
import logging
import calendar
import shutil
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import List, Tuple, Optional, Any, Dict

# 项目根目录
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
os.chdir(_REPO_ROOT)

# 输出目录：backup/data
OUT_DIR = _REPO_ROOT / "backup" / "data"

# 表名 -> (日期列, 类型: "yyyymmdd" | "quarter")，None 表示无日期列、全表导出
TABLE_DATE_CONFIG: Dict[str, Optional[Tuple[str, str]]] = {
    "sys_stock_klines": ("date", "yyyymmdd"),
    "sys_stock_indicators": ("date", "yyyymmdd"),
    "sys_adj_factor_events": ("event_date", "yyyymmdd"),
    "sys_corporate_finance": ("quarter", "quarter"),
    "sys_index_klines": ("date", "yyyymmdd"),
    "sys_index_weight": ("date", "yyyymmdd"),
    "sys_gdp": ("quarter", "quarter"),
    "sys_cpi": ("date", "yyyymmdd"),
    "sys_ppi": ("date", "yyyymmdd"),
    "sys_pmi": ("date", "yyyymmdd"),
    "sys_money_supply": ("date", "yyyymmdd"),
    "sys_shibor": ("date", "yyyymmdd"),
    "sys_lpr": ("date", "yyyymmdd"),
    "sys_tag_value": ("as_of_date", "yyyymmdd"),
    "sys_stock_list": None,
    "sys_index_list": None,
    "sys_industries": None,
    "sys_boards": None,
    "sys_markets": None,
    "sys_stock_industries": None,
    "sys_stock_boards": None,
    "sys_stock_markets": None,
    "sys_stock_industry_map": None,
    "sys_stock_board_map": None,
    "sys_stock_market_map": None,
    "sys_tag_scenario": None,
    "sys_tag_definition": None,
}

DURATION_RE = re.compile(r"^(\d+)(d|m|y)$", re.IGNORECASE)
DATE_FMT = "%Y%m%d"

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def _parse_date(s: str) -> date:
    """YYYYMMDD -> date."""
    return datetime.strptime(s.strip(), DATE_FMT).date()


def _format_date(d: date) -> str:
    return d.strftime(DATE_FMT)


def _parse_duration(s: str) -> Tuple[int, str]:
    """解析 30d / 3m / 2y，返回 (数值, 单位)。"""
    s = s.strip().lower()
    m = DURATION_RE.match(s)
    if not m:
        raise ValueError(f"无效 duration: {s!r}，应为如 30d、3m、2y")
    return int(m.group(1)), m.group(2)


def _add_duration(d: date, num: int, unit: str) -> date:
    """d + duration."""
    if unit == "d":
        return d + timedelta(days=num)
    if unit == "m":
        month = d.month + num
        year = d.year
        while month > 12:
            month -= 12
            year += 1
        while month < 1:
            month += 12
            year -= 1
        day = min(d.day, calendar.monthrange(year, month)[1])
        return date(year, month, day)
    if unit == "y":
        return date(d.year + num, d.month, min(d.day, calendar.monthrange(d.year + num, d.month)[1]))
    raise ValueError(f"未知单位: {unit}")


def _sub_duration(d: date, num: int, unit: str) -> date:
    """d - duration."""
    if unit == "d":
        return d - timedelta(days=num)
    if unit == "m":
        month = d.month - num
        year = d.year
        while month < 1:
            month += 12
            year -= 1
        while month > 12:
            month -= 12
            year += 1
        day = min(d.day, calendar.monthrange(year, month)[1])
        return date(year, month, day)
    if unit == "y":
        return date(d.year - num, d.month, min(d.day, calendar.monthrange(d.year - num, d.month)[1]))
    raise ValueError(f"未知单位: {unit}")


def _date_to_quarter(d: date) -> str:
    """date -> YYYYQn."""
    q = (d.month - 1) // 3 + 1
    return f"{d.year}Q{q}"


def resolve_start_end(
    start: Optional[str],
    end: Optional[str],
    duration: Optional[str],
) -> Tuple[Optional[str], Optional[str]]:
    """
    解析 start/end。优先级：区间(-s,-e) > 正推(-s,-d) > 倒推(-e,-d)。
    返回 (start_yyyymmdd, end_yyyymmdd)，全表时返回 (None, None)。
    """
    if start and end:
        return _format_date(_parse_date(start)), _format_date(_parse_date(end))
    if start and duration:
        n, u = _parse_duration(duration)
        d = _parse_date(start)
        e = _add_duration(d, n, u)
        return _format_date(d), _format_date(e)
    if end and duration:
        n, u = _parse_duration(duration)
        d = _parse_date(end)
        s = _sub_duration(d, n, u)
        return _format_date(s), _format_date(d)
    return None, None


def _serialize_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _rows_to_csv_bytes(rows: List[Dict[str, Any]]) -> bytes:
    if not rows:
        return b""
    keys = list(rows[0].keys())
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=keys, extrasaction="ignore")
    w.writeheader()
    for row in rows:
        w.writerow({k: _serialize_cell(row.get(k)) for k in keys})
    return buf.getvalue().encode("utf-8")


def _build_where(
    date_config: Tuple[str, str],
    start_yyyymmdd: str,
    end_yyyymmdd: str,
) -> Tuple[str, tuple]:
    col, kind = date_config
    if kind == "yyyymmdd":
        return f"{col} >= %s AND {col} <= %s", (start_yyyymmdd, end_yyyymmdd)
    if kind == "quarter":
        start_d = _parse_date(start_yyyymmdd)
        end_d = _parse_date(end_yyyymmdd)
        q_start = _date_to_quarter(start_d)
        q_end = _date_to_quarter(end_d)
        return f"{col} >= %s AND {col} <= %s", (q_start, q_end)
    return "1=1", ()


def run_export(
    table_name: str,
    start: Optional[str],
    end: Optional[str],
    duration: Optional[str],
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

    date_config = TABLE_DATE_CONFIG.get(table_name)
    start_yyyymmdd, end_yyyymmdd = resolve_start_end(start, end, duration)

    if date_config is None:
        # 无日期列：全表导出，忽略日期参数
        where, params = "1=1", ()
        start_yyyymmdd = None
        end_yyyymmdd = None
    elif start_yyyymmdd and end_yyyymmdd:
        where, params = _build_where(date_config, start_yyyymmdd, end_yyyymmdd)
    else:
        raise SystemExit("该表有日期列，请指定 -s -e 或 -s -d 或 -e -d")

    try:
        rows = model.load(condition=where, params=params)
    except Exception as e:
        raise SystemExit(f"查询表 {table_name} 失败: {e}")

    backup_date = date.today().strftime(DATE_FMT)
    # 目录：backup/data/{backup_date}/
    backup_dir = OUT_DIR / backup_date
    backup_dir.mkdir(parents=True, exist_ok=True)

    # 文件名：{table_name}_{start}_{end}.ext 或 {table_name}.ext（无日期）
    if start_yyyymmdd and end_yyyymmdd:
        file_stem = f"{table_name}_{start_yyyymmdd}_{end_yyyymmdd}"
    else:
        file_stem = f"{table_name}"

    ext = "tar.gz" if archive_format == "tar.gz" else "zip"
    archive_path = backup_dir / f"{file_stem}.{ext}"
    csv_name = f"{table_name}.csv"
    csv_bytes = _rows_to_csv_bytes(rows)

    if archive_format == "tar.gz":
        with tarfile.open(archive_path, "w:gz", compresslevel=9) as tf:
            ti = tarfile.TarInfo(name=csv_name)
            ti.size = len(csv_bytes)
            ti.mtime = datetime.now().timestamp()
            tf.addfile(ti, io.BytesIO(csv_bytes))
    else:
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            zf.writestr(csv_name, csv_bytes)

    logger.info("导出 %s -> %s (%d 行)", table_name, archive_path.name, len(rows))


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
        description="按表导出/备份到 backup/data/，文件名 {table}_{backup_date}_{start}_{end}.tar.gz"
    )
    parser.add_argument("-t", "--table", required=True, help="表名，如 sys_corporate_finance")
    parser.add_argument("-s", "--start", default=None, help="起始日期 YYYYMMDD")
    parser.add_argument("-e", "--end", default=None, help="结束日期 YYYYMMDD")
    parser.add_argument(
        "-d",
        "--duration",
        default=None,
        help="时长：30d / 3m / 2y。与 -s 正推或与 -e 倒推",
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

    run_export(
        table_name=args.table.strip(),
        start=args.start,
        end=args.end,
        duration=args.duration,
        archive_format=args.format,
    )
    prune_old_backups(args.keep)


if __name__ == "__main__":
    main()
