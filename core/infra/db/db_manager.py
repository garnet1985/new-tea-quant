"""
DatabaseManager — 挂载 per-backend Engine，对外统一转发。

- ``engine``：mysql / postgresql / duckdb 编排入口
- ``schema_manager``：initialize 后与 engine 共享
- ``storage_registry``：表 → storage_domain（DuckDB 多文件）
"""
from typing import Optional, Dict, List, Any, Callable
from contextlib import contextmanager
from pathlib import Path
import logging

from core.infra.project_context import ProjectContextManager

ctx = ProjectContextManager()  # module-level instance

from core.infra.db.schema_manager import SchemaManager
from core.infra.db.engines._shared.config_parse import parse_database_config
from core.infra.db.storage_registry import StorageRegistry
from core.infra.db.engines.abc.engine_abc import DbEngineAbc
from core.infra.db.engines.meta import EngineConfigMeta, build_engine_meta
from core.infra.db.engines.factory import create_engine


logger = logging.getLogger(__name__)


class DatabaseManager:
    """数据库管理器：按配置 mount 一个 Engine，业务只通过本类或 ``engine`` 访问。"""

    _default_instance = None
    _auto_init_enabled = True

    def __init__(self, config: Dict = None, is_verbose: bool = False):
        if config is None:
            config = ctx.load_database_config()

        self.config = parse_database_config(config)
        self.is_verbose = is_verbose
        self._initialized = False

        database_type = self.config.get("database_type", "postgresql")
        self.storage_registry = StorageRegistry(database_type)

        self.schema_manager = SchemaManager(
            is_verbose=is_verbose,
            database_type=database_type,
        )

        self.engine_meta: EngineConfigMeta = build_engine_meta(
            self.config, is_verbose=is_verbose
        )
        self.engine: Optional[DbEngineAbc] = None

    def _require_engine(self) -> DbEngineAbc:
        if not self._initialized or self.engine is None:
            raise RuntimeError("数据库未初始化，请先调用 initialize()")
        return self.engine

    @classmethod
    def set_default(cls, instance: "DatabaseManager"):
        cls._default_instance = instance
        logger.debug("✅ DatabaseManager 已设置为默认实例")

    @classmethod
    def get_default(cls, auto_init: bool = True) -> "DatabaseManager":
        if cls._default_instance is None:
            if auto_init and cls._auto_init_enabled:
                import threading

                if not hasattr(cls, "_init_lock"):
                    cls._init_lock = threading.Lock()

                with cls._init_lock:
                    if cls._default_instance is None:
                        instance = cls(is_verbose=False)
                        instance.initialize()
                        cls._default_instance = instance
            else:
                raise RuntimeError(
                    "No default DatabaseManager instance. "
                    "Call DatabaseManager.set_default(db) or enable auto_init."
                )

        return cls._default_instance

    @classmethod
    def reset_default(cls):
        if cls._default_instance is not None:
            cls._default_instance.close()
        cls._default_instance = None

    @property
    def uses_engine_path(self) -> bool:
        return self.database_type in ("mysql", "postgresql", "duckdb")

    @property
    def database_type(self) -> str:
        return str(self.config.get("database_type", "postgresql")).lower()

    @property
    def is_duckdb(self) -> bool:
        return self.storage_registry.is_duckdb

    def initialize(self):
        if self._initialized:
            return

        try:
            self.engine = create_engine(self.engine_meta)
            self.rebuild_storage_registry()
            from core.infra.db.engines.duckdb.engine import DuckdbEngine

            if isinstance(self.engine, DuckdbEngine):
                self.engine.rebuild_table_file_map(
                    table_to_domain=self.storage_registry.table_to_domain
                )
            self.engine.initialize()
            self.schema_manager = self.engine.schema_manager
            self._initialized = True

            if self.is_verbose:
                logger.debug(
                    "✅ DatabaseManager 初始化完成（%s Engine）",
                    self.database_type,
                )
        except Exception as e:
            logger.error("❌ DatabaseManager 初始化失败: %s", e)
            raise

    @property
    def adapter(self):
        return self._require_engine().adapter

    def adapter_for_table(self, table_name: str):
        eng = self._require_engine()
        if self.is_duckdb:
            domain = self.get_table_domain(table_name)
            return eng.connector.connection_for_domain(domain)
        return eng.adapter

    def get_table_domain(self, table_name: str) -> str:
        if self.is_duckdb and self.engine is not None:
            from core.infra.db.engines.duckdb.engine import DuckdbEngine

            if isinstance(self.engine, DuckdbEngine):
                return self.engine.resolve_domain(table_name)
        return self.storage_registry.get_domain(table_name)

    def duckdb_file_map_for_table(self, table_name: str):
        if not self.is_duckdb:
            raise RuntimeError("当前 backend 不是 duckdb")
        from core.infra.db.engines.duckdb.engine import DuckdbEngine

        eng = self._require_engine()
        if not isinstance(eng, DuckdbEngine):
            raise RuntimeError("mounted engine 不是 DuckdbEngine")
        return eng.file_map_for_table(table_name)

    def rebuild_storage_registry(self) -> None:
        self.storage_registry = StorageRegistry(self.database_type)
        tables_path = Path(self.schema_manager.tables_dir)
        if not tables_path.exists():
            return
        for schema_py in sorted(tables_path.rglob("schema.py")):
            if not schema_py.is_file():
                continue
            try:
                schema = self.schema_manager.load_schema_from_python(str(schema_py))
                if schema:
                    self.storage_registry.register_schema(schema)
            except Exception as e:
                logger.error("注册 storage_domain 失败 %s: %s", schema_py, e)
        for schema in self.schema_manager.registered_tables.values():
            self.storage_registry.register_schema(schema)

    @contextmanager
    def get_connection(self):
        with self._require_engine().get_connection() as conn:
            yield conn

    @contextmanager
    def transaction(self):
        with self._require_engine().transaction() as cursor:
            yield cursor

    @contextmanager
    def get_sync_cursor(self, domain: Optional[str] = None):
        eng = self._require_engine()
        if self.is_duckdb and domain is not None:
            with eng.get_sync_cursor(domain=domain) as cursor:
                yield cursor
        else:
            with eng.get_sync_cursor() as cursor:
                yield cursor

    @contextmanager
    def get_sync_cursor_for_table(self, table_name: str):
        eng = self._require_engine()
        if self.is_duckdb:
            with eng.get_sync_cursor_for_table(table_name) as cursor:
                yield cursor
        else:
            with eng.get_sync_cursor() as cursor:
                yield cursor

    def connection_factory_for_table(self, table_name: str) -> Callable:
        eng = self._require_engine()
        if self.is_duckdb:
            return eng._connection_factory_for_table(table_name)
        return eng._connection_factory()

    def execute_sync_query(
        self, query: str, params: Any = None, domain: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        执行同步读查询。

        返回契约（由 connector 出口保证，调用方勿再处理 Decimal/numpy）：
        - DECIMAL/NUMERIC 列 → ``float``
        - 整型列 → ``int``
        - NULL → ``None``
        """
        eng = self._require_engine()
        if self.is_duckdb and domain is not None:
            return eng.execute_sync_query(query, params, domain=domain)
        return eng.execute_sync_query(query, params)

    def execute_sync_query_for_table(
        self, table_name: str, query: str, params: Any = None
    ) -> List[Dict[str, Any]]:
        eng = self._require_engine()
        if self.is_duckdb:
            return eng.execute_sync_query_for_table(table_name, query, params)
        return eng.execute_sync_query(query, params)

    def register_table(self, table_name: str, schema: Dict):
        self.storage_registry.register_schema(schema)
        self._require_engine().register_table(table_name, schema)

    def create_registered_tables(self) -> None:
        self._require_engine().create_registered_tables()

    def is_table_exists(self, table_name: str) -> bool:
        return self._require_engine().table_exists(table_name)

    def create_all_base_tables(self) -> None:
        schemas = self.schema_manager.load_all_schemas()
        for _table_name, schema in schemas.items():
            self.storage_registry.register_schema(schema)
        self._require_engine().create_all_tables(schemas)

    def create_table(self, schema: Dict) -> None:
        if schema:
            self.storage_registry.register_schema(schema)
        self._require_engine().create_table(schema)

    def drop_table(self, table_name: str) -> None:
        self._require_engine().drop_table(table_name)

    def load_schema_from_python(self, schema_file: str) -> Dict:
        return self.schema_manager.load_schema_from_python(schema_file)

    def get_table_schema(self, table_name: str) -> Optional[Dict]:
        return self._require_engine().get_table_schema(table_name)

    def get_table_fields(self, table_name: str) -> List[str]:
        return self._require_engine().get_table_fields(table_name)

    def queue_write(
        self,
        table_name: str,
        data_list: List[Dict],
        unique_keys: List[str],
        callback: Callable = None,
    ):
        self._require_engine().queue_write(
            table_name, data_list, unique_keys, callback
        )

    def flush_writes(self, table_name: Optional[str] = None):
        self._require_engine().flush_writes(table_name)

    def get_write_stats(self) -> Dict[str, Any]:
        return self._require_engine().get_write_stats()

    def wait_for_writes(self, timeout: float = 30.0):
        self._require_engine().wait_for_writes(timeout)

    def checkpoint_duckdb(self, domains: Optional[list] = None) -> Dict[str, bool]:
        eng = self.engine
        if eng is not None and hasattr(eng, "checkpoint"):
            return eng.checkpoint(domains=domains)
        return {}

    def close(self):
        if self.engine is not None:
            self.engine.close()
            self.engine = None
        self._initialized = False

    def get_stats(self) -> Dict:
        if self.engine is not None:
            stats = self.engine.get_stats()
            stats["initialized"] = self._initialized
            return stats
        return {
            "initialized": self._initialized,
            "database_type": self.database_type,
        }

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
