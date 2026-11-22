"""duckdb_file_locks：排查 / 清理占用本机 DuckDB 文件的进程。"""

from __future__ import annotations

from typing import Any, Dict

from core.infra.db import Db


def duckdb_file_locks(arguments: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """列出或清理 ``userspace/system/db/*.duckdb`` 文件锁占用。

    常见报错：``Conflicting lock is held`` / ``无法打开 DuckDB（文件被其他进程占用）``。
    """
    args = arguments if isinstance(arguments, dict) else {}
    extra = set(args) - {"kill", "force"}
    if extra:
        return {"ok": False, "error": f"不支持的参数: {', '.join(sorted(extra))}"}

    kill = bool(args.get("kill") or False)
    force = bool(args.get("force") or False)
    try:
        if kill:
            return Db.duckdb.release_file_locks(kill=True, force=force)
        return Db.duckdb.inspect_file_locks()
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"排查失败: {exc}"}


__all__ = ["duckdb_file_locks"]
