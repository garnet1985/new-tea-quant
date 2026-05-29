"""
DuckDBAdapter - DuckDB 嵌入式数据库适配器

单文件单连接；占位符使用 ``?``（与 PostgreSQL 的 ``%s`` 不同，由 normalize_query 处理）。
"""
from __future__ import annotations

import logging
import threading
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

from .base_adapter import BaseDatabaseAdapter

logger = logging.getLogger(__name__)


class DuckDBAdapter(BaseDatabaseAdapter):
    """
    DuckDB 数据库适配器（单域单文件）。

    配置项：
    - db_path: .duckdb 文件路径（相对项目根或绝对路径）
    - threads: 可选，PRAGMA threads
    - memory_limit: 可选，PRAGMA memory_limit
    - read_only: 可选，只读打开（子进程读场景）
    """

    def __init__(self, config: Dict[str, Any], is_verbose: bool = False):
        self.config = config or {}
        self.is_verbose = is_verbose
        self._conn = None
        self._lock = threading.Lock()
        self._initialized = False

    def connect(self, config: Dict[str, Any] = None) -> Any:
        if config:
            self.config = config
        try:
            import duckdb
        except ImportError as e:
            raise ImportError(
                "未安装 duckdb 包，请执行: pip install duckdb"
            ) from e

        db_path = self.config.get("db_path")
        if not db_path:
            raise ValueError("DuckDB 配置缺少 db_path")

        read_only = bool(self.config.get("read_only", False))
        self._conn = self._open_connection(str(db_path), read_only=read_only)

        threads = self.config.get("threads")
        if threads is not None:
            try:
                self._conn.execute(f"PRAGMA threads={int(threads)}")
            except Exception as e:
                logger.debug("DuckDB PRAGMA threads 跳过: %s", e)

        memory_limit = self.config.get("memory_limit")
        if memory_limit:
            try:
                self._conn.execute(f"PRAGMA memory_limit='{memory_limit}'")
            except Exception as e:
                logger.debug("DuckDB PRAGMA memory_limit 跳过: %s", e)

        self._initialized = True
        if self.is_verbose:
            logger.info("✅ DuckDB 已连接: %s (read_only=%s)", db_path, read_only)
        return self._conn

    def _open_connection(self, db_path: str, *, read_only: bool) -> Any:
        """打开连接；WAL 回放失败时删除孤立 .wal 并重试一次。"""
        import duckdb

        try:
            if read_only:
                return duckdb.connect(db_path, read_only=True)
            return duckdb.connect(db_path)
        except Exception as e:
            if not self._is_corrupt_wal_error(e):
                raise
            wal_path = f"{db_path}.wal"
            logger.warning(
                "DuckDB WAL 回放失败，将删除孤立 WAL 后重试: %s (%s)",
                wal_path,
                e,
            )
            from pathlib import Path

            Path(wal_path).unlink(missing_ok=True)
            if read_only:
                return duckdb.connect(db_path, read_only=True)
            return duckdb.connect(db_path)

    @staticmethod
    def _is_corrupt_wal_error(exc: BaseException) -> bool:
        msg = str(exc).lower()
        return "replaying wal" in msg or "wal file" in msg

    def close(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None
        self._initialized = False

    def _ensure_conn(self) -> Any:
        if not self._initialized or self._conn is None:
            if self.config:
                self.connect()
            else:
                raise RuntimeError("DuckDB 适配器未初始化，请先调用 connect()")
        return self._conn

    def _execute(self, query: str, params: Any = None) -> Any:
        query = self.normalize_query(query)
        conn = self._ensure_conn()
        with self._lock:
            if params is None:
                return conn.execute(query)
            return conn.execute(query, params)

    def execute_query(self, query: str, params: Any = None) -> List[Dict[str, Any]]:
        try:
            rel = self._execute(query, params)
            if rel is None:
                return []
            df = rel.fetchdf()
            if df is None or df.empty:
                return []
            return df.to_dict(orient="records")
        except Exception as e:
            logger.error("DuckDB 查询失败: %s\nSQL: %s\nparams: %s", e, query, params)
            raise

    def execute_write(self, query: str, params: Any = None) -> int:
        try:
            rel = self._execute(query, params)
            if rel is None:
                return 0
            try:
                return int(rel.rowcount)
            except Exception:
                return 0
        except Exception as e:
            logger.error("DuckDB 写入失败: %s\nSQL: %s\nparams: %s", e, query, params)
            raise

    def execute_batch(self, query: str, params_list: List[Any]) -> int:
        if not params_list:
            return 0
        total = 0
        query = self.normalize_query(query)
        conn = self._ensure_conn()
        with self._lock:
            for params in params_list:
                rel = conn.execute(query, params)
                try:
                    total += int(rel.rowcount) if rel is not None else 0
                except Exception:
                    pass
        return total

    @contextmanager
    def transaction(self):
        conn = self._ensure_conn()
        try:
            conn.execute("BEGIN TRANSACTION")
            yield _DuckDBTransactionCursor(conn, self._lock)
            with self._lock:
                conn.execute("COMMIT")
        except Exception:
            with self._lock:
                try:
                    conn.execute("ROLLBACK")
                except Exception:
                    pass
            raise

    def get_placeholder(self) -> str:
        return "?"

    def get_connection(self) -> Any:
        return _DuckDBConnectionWrapper(self._ensure_conn(), self)

    def is_table_exists(self, table_name: str) -> bool:
        query = """
            SELECT COUNT(*) AS count
            FROM information_schema.tables
            WHERE table_schema = 'main' AND table_name = ?
        """
        try:
            rows = self.execute_query(query, (table_name,))
            if not rows:
                return False
            row = rows[0]
            val = row.get("count") or row.get("COUNT") or 0
            return int(val) > 0
        except Exception as e:
            logger.error("DuckDB 检查表是否存在失败 %s: %s", table_name, e)
            return False


class _DuckDBTransactionCursor:
    """事务内游标：在持有锁的情况下执行语句。"""

    def __init__(self, conn: Any, lock: threading.Lock) -> None:
        self._conn = conn
        self._lock = lock
        self.rowcount = 0

    def execute(self, query: str, params: Any = None) -> None:
        q = query.replace("%s", "?") if "%s" in query else query
        with self._lock:
            if params is None:
                rel = self._conn.execute(q)
            else:
                rel = self._conn.execute(q, params)
            try:
                self.rowcount = int(rel.rowcount) if rel is not None else 0
            except Exception:
                self.rowcount = 0


class _DuckDBConnectionWrapper:
    """SchemaManager DDL：conn.execute(sql)。"""

    def __init__(self, conn: Any, adapter: DuckDBAdapter) -> None:
        self._conn = conn
        self._adapter = adapter
        self._lock = adapter._lock

    def execute(self, query: str, params: Any = None) -> Any:
        with self._lock:
            if params is None:
                return self._conn.execute(query)
            return self._conn.execute(query, params)

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass
