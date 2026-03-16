#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
按表导入/恢复备份：从 backup/data/{backup_date}/ 下的单表归档导入到指定表。

- 备份目录：backup/data/{backup_date}/，backup_date = YYYYMMDD
- 归档文件名：
    - 全量：{table}.tar.gz | {table}.zip
    - 范围：{table}_{start}_{end}.tar.gz | .zip

导入模式（三选一）：
- 默认（无 -r/-i/-u）：等价于 -r
- -r / --replace: 覆盖模式，导入前 DELETE FROM target_table
- -i / --incremental: 追加模式，不清空，直接 INSERT
- -u / --upsert: upsert 模式（按主键/唯一约束做冲突处理，当前实现为简单 INSERT，后续可按需要扩展）

文件选择顺序（在 backup/data/{backup_date}/ 下）：
1. 先找全量：{table}.tar.gz|zip
2. 若没有，再找范围：{table}_*.tar.gz|zip
3. 若都没有：报错退出
"""
import sys
import os
import re
import csv
import io
import tarfile
import zipfile
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, List

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
os.chdir(_REPO_ROOT)

BACKUP_ROOT = _REPO_ROOT / "backup" / "data"

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def _list_backup_dates() -> List[str]:
    if not BACKUP_ROOT.exists():
        return []
    dates = [
        p.name
        for p in BACKUP_ROOT.iterdir()
        if p.is_dir() and re.fullmatch(r"\d{8}", p.name)
    ]
    dates.sort()
    return dates


def _detect_latest_backup_date() -> Optional[str]:
    dates = _list_backup_dates()
    return dates[-1] if dates else None


def _pick_archive_for_table(backup_date: str, table: str) -> Path:
    """
    在 backup/data/{backup_date}/ 中根据表名选择归档：
    1) 优先全量：{table}.tar.gz|zip
    2) 再范围：{table}_*.tar.gz|zip
    """
    base_dir = BACKUP_ROOT / backup_date
    if not base_dir.exists():
        raise SystemExit(f"备份目录不存在: {base_dir}")

    candidates_full = []
    for ext in (".tar.gz", ".zip"):
        p = base_dir / f"{table}{ext}"
        if p.exists():
            candidates_full.append(p)
    if len(candidates_full) == 1:
        return candidates_full[0]
    if len(candidates_full) > 1:
        raise SystemExit(f"发现多个全量备份文件，请手动处理: {candidates_full}")

    # 范围备份
    pattern = re.compile(rf"^{re.escape(table)}_.+\.(tar\.gz|zip)$")
    ranged = [p for p in base_dir.iterdir() if p.is_file() and pattern.match(p.name)]
    if len(ranged) == 1:
        return ranged[0]
    if len(ranged) > 1:
        raise SystemExit(f"发现多个范围备份文件，请手动处理: {ranged}")

    raise SystemExit(f"在 {base_dir} 下未找到 {table} 的备份文件")


def _read_csv_from_archive(archive_path: Path, inner_name: Optional[str] = None) -> Tuple[List[str], List[dict]]:
    """
    从 .tar.gz 或 .zip 中读取单个 CSV：
    - inner_name 为空时，自动选择第一个 .csv 文件。
    返回 (fieldnames, rows)
    """
    if archive_path.suffix == ".zip":
        with zipfile.ZipFile(archive_path, "r") as zf:
            names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
            if not names:
                raise SystemExit(f"{archive_path} 中未找到 CSV 文件")
            target = inner_name or names[0]
            with zf.open(target) as f:
                text = io.TextIOWrapper(f, encoding="utf-8")
                reader = csv.DictReader(text)
                rows = list(reader)
                return reader.fieldnames or [], rows
    else:
        # 处理 .tar.gz
        with tarfile.open(archive_path, "r:*") as tf:
            members = [m for m in tf.getmembers() if m.name.lower().endswith(".csv")]
            if not members:
                raise SystemExit(f"{archive_path} 中未找到 CSV 文件")
            member = members[0] if inner_name is None else next(
                (m for m in members if m.name == inner_name), members[0]
            )
            f = tf.extractfile(member)
            if f is None:
                raise SystemExit(f"无法从 {archive_path} 读取 {member.name}")
            text = io.TextIOWrapper(f, encoding="utf-8")
            reader = csv.DictReader(text)
            rows = list(reader)
            return reader.fieldnames or [], rows


def _mode_flags(args: argparse.Namespace) -> str:
    """
    从命令行参数解析导入模式。

    同时传多个模式时直接报错。
    """
    flags = [f for f in ("r", "i", "u") if getattr(args, f, False)]
    if len(flags) > 1:
        raise SystemExit("导入模式只能三选一：-r / -i / -u")
    return flags[0] if flags else "r"


def _normalize_db_type(raw: Optional[str]) -> str:
    """
    将配置中的 database_type 统一归一化到 'postgresql' / 'mysql' / 'sqlite' 三类。
    """
    if not raw:
        return "postgresql"
    t = str(raw).lower()
    if t in ("postgresql", "postgres", "pg"):
        return "postgresql"
    if t in ("mysql", "mariadb"):
        return "mysql"
    if "sqlite" in t:
        return "sqlite"
    return "postgresql"


def _resolve_table_names_for_db(
    db_config: dict,
    db_type: str,
    source_logical: str,
    target_logical: str,
) -> Tuple[str, str]:
    """
    根据数据库类型，把逻辑表名转换为当前连接下可用的物理表名。

    - PostgreSQL：schema.table
    - MySQL / SQLite：表名本身
    """
    if db_type == "postgresql":
        pg_cfg = db_config.get("postgresql", {})
        default_schema = pg_cfg.get("pgsql_schema", "public")

        # 源表始终使用默认 schema + 逻辑名
        source_schema = default_schema
        source_sql_name = f"{source_schema}.{source_logical}"

        # 目标表：如果包含 schema 前缀，则使用显式 schema，否则使用默认 schema
        raw_target = target_logical
        if "." in raw_target:
            target_schema, target_table_name = raw_target.split(".", 1)
        else:
            target_schema, target_table_name = default_schema, raw_target
        target_sql_name = f"{target_schema}.{target_table_name}"
        return source_sql_name, target_sql_name

    # MySQL / SQLite：暂时不处理 schema，直接使用表名
    return source_logical, target_logical


def _ensure_target_table(
    cursor,
    db_type: str,
    source_sql_name: str,
    target_sql_name: str,
) -> bool:
    """
    确保目标表存在。如有需要自动创建。

    返回值：
        True  表示通过 DROP + CREATE 新建了表（PostgreSQL 场景）
        False 表示只是确保存在（MySQL/SQLite 或其他方式）
    """
    created_by_drop_create = False

    try:
        if db_type == "postgresql":
            # 删除旧表（如果存在），再按源表结构创建空表（只复制列，不复制约束/索引）
            cursor.execute(f"DROP TABLE IF EXISTS {target_sql_name}")
            cursor.execute(
                f"CREATE TABLE {target_sql_name} AS SELECT * FROM {source_sql_name} WHERE 1=0"
            )
            logger.info("已自动创建目标表: %s <- %s", target_sql_name, source_sql_name)
            created_by_drop_create = True
        elif db_type == "mysql":
            cursor.execute(
                f"CREATE TABLE IF NOT EXISTS {target_sql_name} LIKE {source_sql_name}"
            )
            logger.info("已确保目标表存在: %s (LIKE %s)", target_sql_name, source_sql_name)
        elif db_type == "sqlite":
            cursor.execute(
                f"CREATE TABLE IF NOT EXISTS {target_sql_name} AS SELECT * FROM {source_sql_name} WHERE 1=0"
            )
            logger.info("已确保目标表存在: %s (AS SELECT FROM %s)", target_sql_name, source_sql_name)
    except Exception as e:
        logger.error("自动建表失败（目标=%s, 源=%s）: %s", target_sql_name, source_sql_name, e)
        raise

    return created_by_drop_create


def run_import(
    backup_date: Optional[str],
    table: str,
    target_table: Optional[str],
    mode: str,
) -> None:
    from core.modules.data_manager import DataManager

    dm = DataManager(is_verbose=False)
    dm.initialize()
    db = dm.db
    if not db:
        raise RuntimeError("DataManager 未初始化或数据库不可用")

    # 解析备份日期
    if backup_date is None:
        backup_date = _detect_latest_backup_date()
        if backup_date is None:
            raise SystemExit(f"在 {BACKUP_ROOT} 下未找到任何备份目录")
        logger.info("未指定 -d，使用最近备份日期: %s", backup_date)

    archive_path = _pick_archive_for_table(backup_date, table)
    logger.info("使用备份文件: %s", archive_path)

    # 读取 CSV
    _, rows = _read_csv_from_archive(archive_path, inner_name=f"{table}.csv")
    logger.info("从备份中读取到 %d 行", len(rows))

    target_table = (target_table or table).strip()

    # 模式
    mode = mode or "r"
    if mode not in ("r", "i", "u"):
        raise SystemExit(f"未知导入模式: {mode}")

    db_type = _normalize_db_type(db.config.get("database_type"))

    # 解析源表和目标表在当前 DB 下的实际名字
    source_sql_name, target_sql_name = _resolve_table_names_for_db(
        db_config=db.config,
        db_type=db_type,
        source_logical=table,
        target_logical=target_table,
    )

    # 执行导入（在同一个连接上下文中执行建表 + 删除/清空 + 插入）
    with db.get_sync_cursor() as cursor:
        # 0. 确保目标表存在（必要时自动基于源表创建）
        created_by_drop_create = _ensure_target_table(
            cursor=cursor,
            db_type=db_type,
            source_sql_name=source_sql_name,
            target_sql_name=target_sql_name,
        )

        # 1. 模式：replace / incremental / upsert 预留
        if mode == "r":
            # PostgreSQL 下我们已经通过 DROP + CREATE 保证表为空，再 DELETE 会触发 "relation 不存在" 的历史问题，这里直接跳过
            if not (db_type == "postgresql" and created_by_drop_create):
                cursor.execute(f"DELETE FROM {target_sql_name}")
                logger.info("已清空目标表: %s", target_sql_name)

        if not rows:
            logger.info("无数据可导入，结束")
            return

        columns = list(rows[0].keys())
        col_list = ", ".join(columns)
        placeholders = ", ".join(["%s"] * len(columns))
        insert_sql = f"INSERT INTO {target_sql_name} ({col_list}) VALUES ({placeholders})"

        for row in rows:
            values = [row.get(c) for c in columns]
            cursor.execute(insert_sql, tuple(values))

    logger.info(
        "导入完成：备份日期=%s, 源表=%s, 目标表=%s, 行数=%d, 模式=%s",
        backup_date,
        table,
        target_table,
        len(rows),
        mode,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="从 backup/data/{backup_date}/ 导入单表备份"
    )
    parser.add_argument(
        "-d",
        "--date",
        default=None,
        help="备份日期 YYYYMMDD，省略则使用最近一次备份",
    )
    parser.add_argument(
        "-t",
        "--table",
        required=True,
        help="源表名（备份时的表名），如 sys_corporate_finance",
    )
    parser.add_argument(
        "--target-table",
        default=None,
        help="目标表名，省略时等于 --table",
    )
    parser.add_argument(
        "-r",
        action="store_true",
        help="覆盖模式：导入前 DELETE FROM target_table（默认）",
    )
    parser.add_argument(
        "-i",
        action="store_true",
        help="追加模式：不清空，直接 INSERT",
    )
    parser.add_argument(
        "-u",
        action="store_true",
        help="upsert 模式（预留，将来可按需要扩展为 ON CONFLICT）",
    )
    args = parser.parse_args()

    mode = _mode_flags(args)
    run_import(
        backup_date=args.date,
        table=args.table.strip(),
        target_table=args.target_table,
        mode=mode,
    )


if __name__ == "__main__":
    main()

