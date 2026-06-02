"""
DuckdbConnector — 三 storage_domain 连接与执行。

每域一个 ``DuckdbDomainConnection``（单文件 + 线程锁）；方言见 ``sql_adapter``。
"""
from __future__ import annotations

import logging
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from core.infra.db.duckdb_wal_policy import apply_connect_settings
from core.infra.db.engines.duckdb.settings import DuckdbSettings
from core.infra.db.engines.duckdb.sql_adapter import DuckdbSqlAdapter
from core.infra.db.helpers.duckdb_paths import resolve_duckdb_db_path
from core.infra.db.storage_registry import PRIMARY_DUCKDB_DOMAIN, STORAGE_DOMAINS

logger = logging.getLogger(__name__)


class DuckdbDomainConnection:
    """单域单 .duckdb 文件连接（读写 + 锁）。"""

    def __init__(
        self,
        config: Dict[str, Any],
        is_verbose: bool = False,
        *,
        domain: str = "data",
    ) -> None:
        self.domain = str(domain)
        self.config = dict(config or {})
        self.is_verbose = is_verbose
        self.sql_adapter = DuckdbSqlAdapter()
        self._conn = None
        self._lock = threading.Lock()
        self._initialized = False

    def connect(self, config: Optional[Dict[str, Any]] = None) -> Any:
        if config:
            self.config = dict(config)
        try:
            import duckdb
        except ImportError as e:
            raise ImportError("未安装 duckdb 包，请执行: pip install duckdb") from e

        db_path = self.config.get("db_path")
        if not db_path:
            raise ValueError(f"DuckDB 域 {self.domain!r} 配置缺少 db_path")

        read_only = bool(self.config.get("read_only", False))
        resolved = resolve_duckdb_db_path(str(db_path))
        self.config["db_path"] = resolved
        self._conn = self._open_connection(resolved, read_only=read_only)

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

        if not read_only:
            apply_connect_settings(self._conn, self.config)

        self._initialized = True
        if self.is_verbose:
            logger.info(
                "✅ DuckDB 域 %s 已连接: %s (read_only=%s)",
                self.domain,
                resolved,
                read_only,
            )
        return self._conn

    def _open_connection(self, db_path: str, *, read_only: bool) -> Any:
        import duckdb

        allow_wal_delete = bool(self.config.get("recover_wal_on_replay_failure", False))
        try:
            if read_only:
                return duckdb.connect(db_path, read_only=True)
            return duckdb.connect(db_path)
        except Exception as e:
            if not self._is_corrupt_wal_error(e):
                raise
            wal_path = f"{db_path}.wal"
            if read_only or not allow_wal_delete:
                raise RuntimeError(
                    f"无法打开 DuckDB（WAL 回放失败）: {db_path}。"
                    f" 可能原因：另有进程正在写入、或上次 Ctrl+C 中断后 WAL 与主库不一致。"
                    f" 请先结束所有 renew/写库进程，再用同一进程正常打开以合并 WAL；"
                    f" 不要在写库进行中用只读连接检查数据库。"
                    f" 原始错误: {self._short_exc(e)}"
                ) from e
            logger.warning(
                "DuckDB WAL 回放失败，将删除 %s 后重试: %s",
                wal_path,
                self._short_exc(e),
            )
            Path(wal_path).unlink(missing_ok=True)
            if read_only:
                return duckdb.connect(db_path, read_only=True)
            return duckdb.connect(db_path)

    @staticmethod
    def _short_exc(exc: BaseException) -> str:
        msg = str(exc).strip()
        return msg.split("\n", 1)[0].strip() or repr(exc)

    @staticmethod
    def _is_corrupt_wal_error(exc: BaseException) -> bool:
        msg = str(exc).lower()
        return "replaying wal" in msg or "wal file" in msg

    def close(self) -> None:
        if self._conn is not None:
            try:
                if not bool(self.config.get("read_only", False)):
                    self.checkpoint()
                self._conn.close()
            except Exception:
                pass
            self._conn = None
        self._initialized = False

    def checkpoint(self) -> None:
        if self._conn is None or bool(self.config.get("read_only", False)):
            return
        try:
            with self._lock:
                self._conn.execute("CHECKPOINT")
        except Exception as e:
            logger.warning("DuckDB CHECKPOINT 失败 domain=%s: %s", self.domain, e)

    def _ensure_conn(self) -> Any:
        if not self._initialized or self._conn is None:
            if self.config:
                self.connect()
            else:
                raise RuntimeError(
                    f"DuckdbDomainConnection[{self.domain}] 未初始化，请先 connect()"
                )
        return self._conn

    def _execute(self, query: str, params: Any = None) -> Any:
        query = self.sql_adapter.normalize_query(query)
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
            logger.error("DuckDB 查询失败 domain=%s: %s\nSQL: %s", self.domain, e, query)
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
            logger.error("DuckDB 写入失败 domain=%s: %s\nSQL: %s", self.domain, e, query)
            raise

    def execute_batch(self, query: str, params_list: List[Any]) -> int:
        if not params_list:
            return 0
        total = 0
        query = self.sql_adapter.normalize_query(query)
        conn = self._ensure_conn()
        with self._lock:
            for params in params_list:
                rel = conn.execute(query, params) if params is not None else conn.execute(query)
                try:
                    total += int(rel.rowcount) if rel is not None else 0
                except Exception:
                    pass
        return total

    @contextmanager
    def transaction(self) -> Iterator[Any]:
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

    def get_connection(self) -> Any:
        return _DuckDBConnectionWrapper(self._ensure_conn(), self)

    def is_table_exists(self, table_name: str) -> bool:
        query, params = self.sql_adapter.table_exists_query_and_params(table_name)
        try:
            rows = self.execute_query(query, params)
            return self.sql_adapter.parse_exists_count(rows[0] if rows else {})
        except Exception as e:
            logger.error("DuckDB 检查表失败 domain=%s table=%s: %s", self.domain, table_name, e)
            return False


class _DuckDBTransactionCursor:
    def __init__(self, conn: Any, lock: threading.Lock) -> None:
        self._conn = conn
        self._lock = lock
        self.rowcount = 0

    def execute(self, query: str, params: Any = None) -> None:
        q = query.replace("%s", "?") if "%s" in query else query
        with self._lock:
            rel = self._conn.execute(q, params) if params is not None else self._conn.execute(q)
            try:
                self.rowcount = int(rel.rowcount) if rel is not None else 0
            except Exception:
                self.rowcount = 0


class _DuckDBConnectionWrapper:
    def __init__(self, conn: Any, domain_conn: DuckdbDomainConnection) -> None:
        self._conn = conn
        self._domain_conn = domain_conn
        self._lock = domain_conn._lock

    def execute(self, query: str, params: Any = None) -> Any:
        with self._lock:
            if params is None:
                return self._conn.execute(query)
            return self._conn.execute(query, params)

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass


class DuckdbConnector:
    """按 storage_domain 管理多个 DuckdbDomainConnection。"""

    def __init__(
        self,
        settings: DuckdbSettings | Dict[str, Any],
        *,
        is_verbose: bool = False,
    ) -> None:
        if isinstance(settings, dict):
            settings = DuckdbSettings.from_dict(settings)
        self.settings = settings
        self.backend_config = settings.as_dict()
        self.is_verbose = is_verbose
        self._domains: Dict[str, DuckdbDomainConnection] = {}

    @property
    def domain_connections(self) -> Dict[str, DuckdbDomainConnection]:
        return self._domains

    def connect_all_domains(self) -> None:
        shared = self.settings.shared_connector_dict()
        self._domains = {}
        for domain in sorted(STORAGE_DOMAINS):
            dom = self.settings.domains[domain]
            merged = dom.as_dict(shared)
            conn = DuckdbDomainConnection(merged, is_verbose=self.is_verbose, domain=domain)
            conn.connect()
            self._domains[domain] = conn

        if PRIMARY_DUCKDB_DOMAIN not in self._domains:
            raise RuntimeError("DuckDB 主域 data 未创建")

    def close_all(self) -> None:
        for conn in self._domains.values():
            conn.close()
        self._domains.clear()

    def connection_for_domain(self, domain: str) -> DuckdbDomainConnection:
        d = str(domain or PRIMARY_DUCKDB_DOMAIN).lower()
        conn = self._domains.get(d)
        if conn is None:
            raise KeyError(f"未知 DuckDB 存储域: {domain!r}")
        return conn

    def primary(self) -> DuckdbDomainConnection:
        return self.connection_for_domain(PRIMARY_DUCKDB_DOMAIN)

    @contextmanager
    def connection(self, domain: Optional[str] = None) -> Iterator[Any]:
        """SchemaManager DDL：借域连接包装对象。"""
        domain_conn = self.connection_for_domain(domain or PRIMARY_DUCKDB_DOMAIN)
        wrapper = domain_conn.get_connection()
        try:
            yield wrapper
        finally:
            pass

    def execute_query(
        self, query: str, params: Any = None, *, domain: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        return self.connection_for_domain(domain or PRIMARY_DUCKDB_DOMAIN).execute_query(
            query, params
        )

    def execute_write(
        self, query: str, params: Any = None, *, domain: Optional[str] = None
    ) -> int:
        return self.connection_for_domain(domain or PRIMARY_DUCKDB_DOMAIN).execute_write(
            query, params
        )

    @contextmanager
    def transaction(self, domain: Optional[str] = None) -> Iterator[Any]:
        with self.connection_for_domain(domain or PRIMARY_DUCKDB_DOMAIN).transaction() as cur:
            yield cur

    def checkpoint(self, domain: Optional[str] = None) -> Dict[str, bool]:
        results: Dict[str, bool] = {}
        targets = (
            [str(domain)]
            if domain is not None
            else sorted(self._domains.keys())
        )
        for d in targets:
            conn = self._domains.get(d)
            if conn is None:
                continue
            if bool(conn.config.get("read_only", False)):
                continue
            try:
                conn.checkpoint()
                results[d] = True
            except Exception as e:
                logger.warning("DuckDB CHECKPOINT 失败 domain=%s: %s", d, e)
                results[d] = False
        return results


# 旧路径兼容
DuckDBAdapter = DuckdbDomainConnection
