"""DuckDB 文件路径解析（落在 userspace/system/db/）。"""
from __future__ import annotations

from pathlib import Path

from core.infra.project_context import PathManager


def resolve_duckdb_db_path(db_path: str) -> str:
    """
    将配置中的 db_path 解析为绝对路径，并确保父目录存在。

    相对路径相对于 ``userspace/system/db/``；绝对路径原样使用。
    """
    if not db_path or not str(db_path).strip():
        raise ValueError("DuckDB db_path 不能为空")

    raw = Path(str(db_path).strip())
    if raw.is_absolute():
        resolved = raw
    else:
        resolved = PathManager.get_system_db_directory() / raw

    resolved.parent.mkdir(parents=True, exist_ok=True)
    return str(resolved.resolve())
