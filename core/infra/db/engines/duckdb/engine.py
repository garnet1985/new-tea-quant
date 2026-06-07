"""
DuckdbEngine — DuckDB 三域引擎（连接、写 Pipeline、table_operator）。
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Callable, Dict, Iterator, Optional

from core.infra.db.engines.duckdb.wal_policy import install_sigint_checkpoint_handler_for_engine
from core.infra.db.engines.abc.engine_abc import DbEngineAbc
from core.infra.db.engines.abc.table_abc import DbTableAbc
from core.infra.db.engines.duckdb.connector import DuckdbConnector
from core.infra.db.engines.duckdb.domain_catalog import (
    DuckdbDomainCatalog,
    DuckdbTableFileMap,
)
from core.infra.db.engines.duckdb.table_operator import DuckdbTableOperator
from core.infra.db.engines.duckdb.write_pipeline import WritePipeline
from core.infra.db.engines.meta import EngineConfigMeta
from core.infra.db.engines._shared.cursor import DatabaseCursor
from core.infra.db.engines._shared.dialect import quote_identifier_for_dialect
from core.infra.db.schema_manager import SchemaManager
from core.infra.db.storage_registry import (
    PRIMARY_DUCKDB_DOMAIN,
    normalize_storage_domain,
)

logger = logging.getLogger(__name__)


class DuckdbEngine(DbEngineAbc):
    engine_key = "duckdb"

    def __init__(self, meta: EngineConfigMeta, *, is_verbose: bool = False) -> None:
        super().__init__(meta, is_verbose=is_verbose)
        self._duckdb_settings = meta.require_duckdb()
        self.connector = DuckdbConnector(self._duckdb_settings, is_verbose=is_verbose)
        self.schema_manager = SchemaManager(
            is_verbose=is_verbose,
            database_type=self.engine_key,
        )
        self._file_catalog: Optional[DuckdbDomainCatalog] = None
        self._write_pipelines: Dict[str, WritePipeline] = {}
        self._checkpoint_after_write = self._duckdb_settings.checkpoint_after_write

    def rebuild_table_file_map(
        self,
        schemas: Optional[Dict[str, Dict[str, Any]]] = None,
        *,
        table_to_domain: Optional[Dict[str, str]] = None,
    ) -> DuckdbDomainCatalog:
        """
        根据 schema 动态构建表 → 域 → 文件映射（内存）。

        ``schemas``：``load_all_schemas()`` 结果；省略则现加载 core/tables + 已注册表。
        ``table_to_domain``：若 Manager 已 ``rebuild_storage_registry``，可直接传入其 ``table_to_domain``。
        """
        if table_to_domain is not None:
            self._file_catalog = DuckdbDomainCatalog.build(
                self._duckdb_settings, table_to_domain
            )
            return self._file_catalog

        if schemas is None:
            schemas = dict(self.schema_manager.load_all_schemas())
            schemas.update(self.schema_manager.registered_tables)
        self._file_catalog = DuckdbDomainCatalog.from_schemas(
            self._duckdb_settings, schemas
        )
        return self._file_catalog

    def file_map_for_table(self, table_name: str) -> DuckdbTableFileMap:
        """传入表名，返回域 + 配置路径 + 绝对路径。"""
        return self._require_file_catalog().file_map_for_table(table_name)

    def resolve_domain(self, table_name: str) -> str:
        return self._require_file_catalog().resolve_domain(table_name)

    def resolve_db_path(self, table_name: str) -> str:
        return self._require_file_catalog().resolve_db_path(table_name)

    @property
    def adapter(self):
        """主域 ``data`` 的 domain connection。"""
        if not self._initialized:
            raise RuntimeError("DuckdbEngine 未 initialize")
        return self.connector.primary()

    def initialize(self) -> None:
        if self._initialized:
            return
        if self._file_catalog is None:
            self.rebuild_table_file_map()
        self.connector.connect_all_domains()
        for domain, _conn in self.connector.domain_connections.items():
            self._write_pipelines[domain] = WritePipeline(
                domain,
                self,
                checkpoint_after_write=self._checkpoint_after_write,
            )
        install_sigint_checkpoint_handler_for_engine(self, self.meta.raw_config)
        self._initialized = True
        if self.is_verbose:
            logger.debug(
                "duckdb Engine 初始化完成（%s 域，%s 张表已映射）",
                len(self._write_pipelines),
                self._file_catalog.table_count if self._file_catalog else 0,
            )

    def close(self) -> None:
        for pipeline in self._write_pipelines.values():
            pipeline.shutdown()
        self._write_pipelines.clear()
        self.connector.close_all()
        self._table_operator_cache.clear()
        self._initialized = False

    def table_operator(self, table_name: str) -> DbTableAbc:
        name = str(table_name)
        cached = self._table_operator_cache.get(name)
        if cached is not None:
            return cached
        op = DuckdbTableOperator(self, name)
        self._table_operator_cache[name] = op
        return op

    def _table_operator_for_domain(self, table_name: str, domain: str) -> DuckdbTableOperator:
        """WritePipeline worker 用：走 _insert_sync，不再入队。"""
        return DuckdbTableOperator(self, table_name)

    def _pipeline_for_domain(self, domain: str) -> WritePipeline:
        pipeline = self._write_pipelines.get(domain)
        if pipeline is None:
            raise KeyError(f"未找到域 {domain!r} 的 WritePipeline")
        return pipeline

    @contextmanager
    def get_connection(self, domain: Optional[str] = None) -> Iterator[Any]:
        self._require_ready()
        with self.connector.connection(domain=domain or PRIMARY_DUCKDB_DOMAIN) as conn:
            yield conn

    @contextmanager
    def get_connection_for_table(self, table_name: str) -> Iterator[Any]:
        domain = self.resolve_domain(table_name)
        with self.get_connection(domain=domain) as conn:
            yield conn

    @contextmanager
    def transaction(self, domain: Optional[str] = None) -> Iterator[Any]:
        self._require_ready()
        with self.connector.transaction(domain=domain or PRIMARY_DUCKDB_DOMAIN) as cursor:
            yield cursor

    @contextmanager
    def get_sync_cursor(self, domain: Optional[str] = None) -> Iterator[DatabaseCursor]:
        self._require_ready()
        conn = self.connector.connection_for_domain(domain or PRIMARY_DUCKDB_DOMAIN)
        cursor = DatabaseCursor(conn)
        try:
            yield cursor
        finally:
            cursor.close()

    @contextmanager
    def get_sync_cursor_for_table(self, table_name: str) -> Iterator[DatabaseCursor]:
        domain = self.resolve_domain(table_name)
        with self.get_sync_cursor(domain=domain) as cursor:
            yield cursor

    def execute_sync_query(
        self, query: str, params: Any = None, *, domain: Optional[str] = None
    ) -> list:
        self._require_ready()
        return self.connector.execute_query(query, params, domain=domain)

    def execute_sync_query_for_table(
        self, table_name: str, query: str, params: Any = None
    ) -> list:
        return self.execute_sync_query(
            query, params, domain=self.resolve_domain(table_name)
        )

    def execute_write(
        self, query: str, params: Any = None, *, domain: Optional[str] = None
    ) -> int:
        self._require_ready()
        return self.connector.execute_write(query, params, domain=domain)

    def ensure_storage(self) -> None:
        if not self._initialized:
            self.initialize()

    def create_table(self, schema: Dict[str, Any]) -> None:
        self._require_ready()
        table_name = schema.get("name") or schema.get("table_name", "")
        factory = self._connection_factory_for_table(str(table_name))
        self.schema_manager.create_table_with_indexes(schema, factory)

    def create_all_tables(self, schemas: Optional[Dict[str, Dict[str, Any]]] = None) -> None:
        self._require_ready()
        if schemas is None:
            schemas = self.schema_manager.load_all_schemas()
        for table_name, schema in schemas.items():
            try:
                self.create_table(schema)
            except Exception as e:
                logger.error("创建表失败 %r: %s", table_name, e)

    def register_table(self, table_name: str, schema: Dict[str, Any]) -> None:
        normalize_storage_domain(
            schema.get("storage_domain"), table_name=table_name
        )
        self.schema_manager.register_table(table_name, schema)
        if self._file_catalog is None:
            self.rebuild_table_file_map({table_name: schema})
        else:
            self._file_catalog.register_schema(self._duckdb_settings, schema)
        if self._initialized:
            self.create_table(schema)

    def create_registered_tables(self) -> None:
        self._require_ready()
        for table_name, schema in self.schema_manager.registered_tables.items():
            try:
                factory = self._connection_factory_for_table(table_name)
                self.schema_manager.create_table_with_indexes(schema, factory)
            except Exception as e:
                logger.error("创建注册表失败 %r: %s", table_name, e)

    def table_exists(self, table_name: str) -> bool:
        self._require_ready()
        domain = self.resolve_domain(table_name)
        return self.connector.connection_for_domain(domain).is_table_exists(table_name)

    def drop_table(self, table_name: str) -> None:
        self._require_ready()
        quoted = quote_identifier_for_dialect("duckdb", table_name)
        domain = self.resolve_domain(table_name)
        self.connector.execute_write(
            f"DROP TABLE IF EXISTS {quoted}",
            domain=domain,
        )

    def get_table_schema(self, table_name: str) -> Optional[Dict[str, Any]]:
        return self.schema_manager.get_table_schema(table_name)

    def get_table_fields(self, table_name: str) -> list:
        return self.schema_manager.get_table_fields(table_name)

    def flush_writes(self, table_name: Optional[str] = None) -> None:
        if table_name is not None:
            domain = self.resolve_domain(table_name)
            self._pipeline_for_domain(domain).flush(table_name)
            return
        for pipeline in self._write_pipelines.values():
            pipeline.flush()

    def wait_for_writes(self, timeout: float = 30.0) -> None:
        for pipeline in self._write_pipelines.values():
            pipeline.wait(timeout)

    def get_write_stats(self) -> Dict[str, Any]:
        return {d: p.get_stats() for d, p in self._write_pipelines.items()}

    def queue_write(
        self,
        table_name: str,
        data_list: list,
        unique_keys: list,
        callback: Optional[Callable] = None,
    ) -> None:
        self._require_ready()
        op = self.table_operator(table_name)
        if unique_keys:
            written = op.upsert(data_list, unique_keys)
        else:
            written = op.insert(data_list, None)
        if callback:
            callback(table_name, written)

    def get_stats(self) -> Dict[str, Any]:
        stats: Dict[str, Any] = {
            "engine_key": self.engine_key,
            "initialized": self._initialized,
            "domains": list(self.connector.domain_connections.keys()),
            "write_pipelines": self.get_write_stats(),
        }
        if self._file_catalog is not None:
            stats["table_file_map_size"] = self._file_catalog.table_count
        return stats

    def _require_file_catalog(self) -> DuckdbDomainCatalog:
        if self._file_catalog is None:
            raise RuntimeError(
                "DuckDB 表文件映射未构建，请先 initialize() 或 rebuild_table_file_map()"
            )
        return self._file_catalog

    def checkpoint(self, domains: Optional[list] = None) -> Dict[str, bool]:
        """DuckDB 专有：合并 WAL。"""
        self._require_ready()
        if domains is not None:
            results: Dict[str, bool] = {}
            for d in domains:
                results.update(self.connector.checkpoint(d))
            return results
        return self.connector.checkpoint()

    def _require_ready(self) -> None:
        if not self._initialized:
            raise RuntimeError(
                f"{type(self).__name__} 未 initialize，请先调用 initialize()"
            )

    def _connection_factory_for_table(self, table_name: str) -> Callable:
        domain = self.resolve_domain(table_name)

        @contextmanager
        def get_connection():
            with self.connector.connection(domain=domain) as conn:
                yield conn

        return get_connection
