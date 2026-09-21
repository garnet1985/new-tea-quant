"""把归档里的 CSV 交给数据库直接装入，不经过 Python 字典。"""
from __future__ import annotations

import csv
import shutil
import tarfile
import tempfile
import zipfile
from pathlib import Path
from typing import Callable, Dict, List, Optional

# read_csv 默认把空字段当成 NULL。用一个导出不会写出的哨兵，空字符串才能留下来。
_DUCKDB_NULLSTR = "NTQ_CSV_NULL"

_TEXT_TYPES = frozenset(
    {
        "",
        "varchar",
        "char",
        "character",
        "text",
        "string",
        "uuid",
        "enum",
    }
)


def schema_has_json(schema: Optional[dict]) -> bool:
    for field in (schema or {}).get("fields") or []:
        if str(field.get("type") or "").lower() in ("json", "jsonb"):
            return True
    return False


def field_types(schema: Optional[dict]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for field in (schema or {}).get("fields") or []:
        name = field.get("name")
        if name:
            out[str(name)] = str(field.get("type") or "").lower()
    return out


def _is_text(field_type: str) -> bool:
    return field_type in _TEXT_TYPES


def _select_expr(quoted_col: str, field_type: str) -> str:
    if _is_text(field_type):
        return quoted_col
    return f"NULLIF({quoted_col}, '')"


def _header(csv_path: Path) -> List[str]:
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        row = next(csv.reader(handle), None)
    if not row:
        return []
    return [cell.strip() for cell in row if cell.strip()]


def _skip_member(name: str) -> bool:
    parts = name.replace("\\", "/").split("/")
    if "__MACOSX" in parts:
        return True
    base = parts[-1]
    return base.startswith("._") or (base.startswith(".") and base not in (".", ".."))


def extract_csv(archive: Path, table_name: str, dest: Path) -> bool:
    """把归档中的 CSV 写到 dest。没有 CSV 时返回 False。"""
    archive = Path(archive)
    if archive.suffix.lower() == ".csv":
        if not archive.is_file() or archive.stat().st_size == 0:
            return False
        shutil.copyfile(archive, dest)
        return True

    target_name = f"{table_name}.csv"
    names: List[str] = []
    if archive.name.lower().endswith(".zip"):
        with zipfile.ZipFile(archive, "r") as zf:
            for info in zf.infolist():
                if info.is_dir() or _skip_member(info.filename):
                    continue
                if info.filename.lower().endswith(".csv"):
                    names.append(info.filename)
            pick = target_name if target_name in names else (names[0] if names else None)
            if pick is None:
                return False
            with zf.open(pick) as src, dest.open("wb") as out:
                shutil.copyfileobj(src, out)
        return dest.stat().st_size > 0

    with tarfile.open(archive, "r:*") as tf:
        members = []
        for member in tf.getmembers():
            if not member.isfile() or _skip_member(member.name):
                continue
            if member.name.lower().endswith(".csv"):
                members.append(member)
        if not members:
            return False
        chosen = next((m for m in members if Path(m.name).name == target_name), members[0])
        extracted = tf.extractfile(chosen)
        if extracted is None:
            return False
        with extracted, dest.open("wb") as out:
            shutil.copyfileobj(extracted, out)
    return dest.stat().st_size > 0


def _scalar_count(cursor, target_sql: str) -> int:
    cursor.execute(f"SELECT COUNT(*) AS cnt FROM {target_sql}")
    row = cursor.fetchone()
    if row is None:
        return 0
    if isinstance(row, dict):
        return int(next(iter(row.values())))
    return int(row[0])


def _insert_from_stage(
    cursor,
    *,
    target_sql: str,
    stage_sql: str,
    header: List[str],
    type_by_name: Dict[str, str],
    quote: Callable[[str], str],
) -> None:
    col_sql = ", ".join(quote(name) for name in header)
    select_sql = ", ".join(
        _select_expr(quote(name), type_by_name.get(name, "varchar")) for name in header
    )
    cursor.execute(
        f"INSERT INTO {target_sql} ({col_sql}) SELECT {select_sql} FROM {stage_sql}"
    )


def copy_csv_file(
    cursor,
    *,
    database_type: str,
    target_sql: str,
    csv_path: Path,
    type_by_name: Dict[str, str],
    quote: Callable[[str], str],
) -> int:
    """把一个 CSV 文件追加进已清空（或已部分导入）的目标表。返回本次行数。"""
    header = _header(csv_path)
    if not header:
        return 0
    before = _scalar_count(cursor, target_sql)
    if database_type == "duckdb":
        col_sql = ", ".join(quote(name) for name in header)
        select_sql = ", ".join(
            _select_expr(quote(name), type_by_name.get(name, "varchar")) for name in header
        )
        cursor.execute(
            f"INSERT INTO {target_sql} ({col_sql}) "
            f"SELECT {select_sql} FROM read_csv(%s, header=true, all_varchar=true, "
            f"nullstr='{_DUCKDB_NULLSTR}')",
            [str(csv_path)],
        )
    elif database_type == "postgresql":
        cols = ", ".join(f"{quote(name)} TEXT" for name in header)
        cursor.execute("DROP TABLE IF EXISTS ntq_csv_import")
        cursor.execute(f"CREATE TEMP TABLE ntq_csv_import ({cols})")
        with csv_path.open("r", encoding="utf-8", newline="") as handle:
            cursor.copy_expert(
                "COPY ntq_csv_import FROM STDIN WITH (FORMAT csv, HEADER true)",
                handle,
            )
        _insert_from_stage(
            cursor,
            target_sql=target_sql,
            stage_sql="ntq_csv_import",
            header=header,
            type_by_name=type_by_name,
            quote=quote,
        )
        cursor.execute("DROP TABLE IF EXISTS ntq_csv_import")
    else:
        raise ValueError(f"不支持直接 CSV 导入的数据库: {database_type}")
    return _scalar_count(cursor, target_sql) - before


def import_archives(
    cursor,
    *,
    database_type: str,
    target_sql: str,
    archives: List[Path],
    table_name: str,
    type_by_name: Dict[str, str],
    quote: Callable[[str], str],
) -> int:
    total = 0
    with tempfile.TemporaryDirectory(prefix="ntq_csv_import_") as tmp:
        dest = Path(tmp) / "part.csv"
        for archive in archives:
            if dest.exists():
                dest.unlink()
            if not extract_csv(Path(archive), table_name, dest):
                continue
            total += copy_csv_file(
                cursor,
                database_type=database_type,
                target_sql=target_sql,
                csv_path=dest,
                type_by_name=type_by_name,
                quote=quote,
            )
    return total
