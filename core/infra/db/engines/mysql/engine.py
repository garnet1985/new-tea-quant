"""
MysqlEngine — MySQL 引擎编排（连接、DDL、写队列、table_operator）。
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Callable, Dict, Iterator, Optional

from core.infra.db.engines.abc.engine_abc import DbEngineAbc
from core.infra.db.engines.abc.table_abc import DbTableAbc
from core.infra.db.engines.meta import EngineConfigMeta
from core.infra.db.engines.mysql.connector import MysqlConnector
from core.infra.db.engines.mysql.table_operator import MysqlTableOperator
from core.infra.db.helpers.db_helpers import DBHelper, DatabaseCursor
from core.infra.db.schema_management.schema_manager import SchemaManager
from core.infra.db.table_queriers.services.batch_operation_queue import BatchWriteQueue

logger = logging.getLogger(__name__)


class _WriteQueueHost:
    """BatchWriteQueue 需要的 table_manager 兼容面。"""

    def __init__(self, engine: MysqlEngine) -> None:
        self._engine = engine

    @property
    def adapter(self):
        return self._engine.connector

    @property
    def config(self) -> Dict[str, Any]:
        return self._engine.meta.raw_config

    def _direct_write(
        self,
        table_name: str,
        data_list: list,
        unique_keys: list,
        callback: Optional[Callable] = None,
    ) -> None:
        self._engine._direct_write(table_name, data_list, unique_keys, callback)


class MysqlEngine(DbEngineAbc):
    engine_key = "mysql"

    def __init__(self, meta: EngineConfigMeta, *, is_verbose: bool = False) -> None:
        super().__init__(meta, is_verbose=is_verbose)
        self.connector = MysqlConnector(meta.require_mysql(), is_verbose=is_verbose)
        self.schema_manager = SchemaManager(
            is_verbose=is_verbose,
            database_type=self.engine_key,
        )
        self._write_queue: Optional[BatchWriteQueue] = None

    @property
    def adapter(self):
        """兼容 DatabaseManager.adapter / 旧 BatchWriteQueue。"""
        return self.connector

    def initialize(self) -> None:
        if self._initialized:
            return
        self.connector.connect()
        self._init_write_queue()
        self._initialized = True
        if self.is_verbose:
            logger.debug("mysql Engine 初始化完成")

    def close(self) -> None:
        if self._write_queue is not None:
            self._write_queue.shutdown()
            self._write_queue = None
        self.connector.close()
        self._table_operator_cache.clear()
        self._initialized = False

    def table_operator(self, table_name: str) -> DbTableAbc:
        name = str(table_name)
        cached = self._table_operator_cache.get(name)
        if cached is not None:
            return cached
        op = MysqlTableOperator(self, name)
        self._table_operator_cache[name] = op
        return op

    @contextmanager
    def get_connection(self) -> Iterator[Any]:
        self._require_ready()
        with self.connector.connection() as conn:
            yield conn

    @contextmanager
    def transaction(self) -> Iterator[Any]:
        self._require_ready()
        with self.connector.transaction() as cursor:
            yield cursor

    @contextmanager
    def get_sync_cursor(self) -> Iterator[DatabaseCursor]:
        self._require_ready()
        cursor = DatabaseCursor(self.connector)
        try:
            yield cursor
        finally:
            cursor.close()

    def execute_sync_query(self, query: str, params: Any = None) -> list:
        self._require_ready()
        return self.connector.execute_query(query, params)

    def execute_write(self, query: str, params: Any = None) -> int:
        self._require_ready()
        return self.connector.execute_write(query, params)

    def ensure_storage(self) -> None:
        if not self._initialized:
            self.initialize()

    def create_table(self, schema: Dict[str, Any]) -> None:
        self._require_ready()
        self.schema_manager.create_table_with_indexes(schema, self._connection_factory())

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
        self.schema_manager.register_table(table_name, schema)
        if self._initialized:
            self.create_table(schema)

    def create_registered_tables(self) -> None:
        self._require_ready()
        self.schema_manager.create_registered_tables(self._connection_factory())

    def table_exists(self, table_name: str) -> bool:
        self._require_ready()
        return self.connector.is_table_exists(table_name)

    def drop_table(self, table_name: str) -> None:
        self._require_ready()
        qualified = DBHelper.sql_qualify_table_name(self.meta.raw_config, table_name)
        quoted = DBHelper.quote_identifier_for_dialect(self.engine_key, qualified)
        self.connector.execute_write(f"DROP TABLE IF EXISTS {quoted}")

    def get_table_schema(self, table_name: str) -> Optional[Dict[str, Any]]:
        return self.schema_manager.get_table_schema(table_name)

    def get_table_fields(self, table_name: str) -> list:
        return self.schema_manager.get_table_fields(table_name)

    def flush_writes(self, table_name: Optional[str] = None) -> None:
        if self._write_queue is not None:
            self._write_queue.flush(table_name)

    def wait_for_writes(self, timeout: float = 30.0) -> None:
        if self._write_queue is not None:
            self._write_queue.wait_for_writes(timeout)

    def get_write_stats(self) -> Dict[str, Any]:
        if self._write_queue is not None:
            return self._write_queue.get_stats()
        return {}

    def queue_write(
        self,
        table_name: str,
        data_list: list,
        unique_keys: list,
        callback: Optional[Callable] = None,
    ) -> None:
        self._require_ready()
        if self._write_queue is None:
            self._direct_write(table_name, data_list, unique_keys, callback)
            return
        self._write_queue.enqueue(table_name, data_list, unique_keys, callback)

    def _direct_write(
        self,
        table_name: str,
        data_list: list,
        unique_keys: list,
        callback: Optional[Callable] = None,
    ) -> None:
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
        }
        if self._write_queue is not None:
            stats["write_queue"] = self._write_queue.get_stats()
        cfg = self.meta.backend_config
        stats["database"] = cfg.get("database")
        stats["host"] = cfg.get("host")
        stats["port"] = cfg.get("port")
        return stats

    def _init_write_queue(self) -> None:
        bw = self.meta.batch_write
        if not bw.enable:
            self._write_queue = None
            return
        self._write_queue = BatchWriteQueue(
            table_manager=_WriteQueueHost(self),
            batch_size=bw.batch_size,
            flush_interval=bw.flush_interval,
            enable=True,
            insert_batch_size=bw.insert_batch_size,
        )

    def _require_ready(self) -> None:
        if not self._initialized:
            raise RuntimeError(
                f"{type(self).__name__} 未 initialize，请先调用 initialize()"
            )

    def _connection_factory(self) -> Callable:
        @contextmanager
        def get_connection():
            with self.connector.connection() as conn:
                yield conn

        return get_connection
