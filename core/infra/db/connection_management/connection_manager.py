"""
ConnectionManager - 连接和事务管理

职责：
- 数据库适配器创建和初始化
- 连接获取和释放
- 事务管理
- 游标管理
- DuckDB 多存储域：每域独立适配器，主连接为 data 域
"""
from typing import Optional, Dict, Any
from contextlib import contextmanager
import logging

from core.infra.db.table_queriers.adapters.factory import DatabaseAdapterFactory
from core.infra.db.table_queriers.adapters.base_adapter import BaseDatabaseAdapter
from core.infra.db.helpers.db_helpers import DatabaseCursor
from core.infra.db.storage_registry import STORAGE_DOMAINS, PRIMARY_DUCKDB_DOMAIN


logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    连接和事务管理器
    
    职责：
    - 数据库适配器创建和初始化
    - 连接获取和释放
    - 事务管理
    - 游标管理
    """
    
    def __init__(self, config: Dict, is_verbose: bool = False):
        """
        初始化连接管理器
        
        Args:
            config: 数据库配置
            is_verbose: 是否输出详细日志
        """
        self.config = config
        self.is_verbose = is_verbose
        self.adapter: Optional[BaseDatabaseAdapter] = None
        self.domain_adapters: Dict[str, BaseDatabaseAdapter] = {}
        self._initialized = False

    @property
    def database_type(self) -> str:
        return str(self.config.get("database_type", "postgresql")).lower()

    @property
    def is_duckdb(self) -> bool:
        return self.database_type == "duckdb"
    
    def initialize(self):
        """
        初始化数据库连接
        
        步骤：
        1. 使用适配器工厂创建适配器（或 DuckDB 多域适配器）
        2. 连接数据库
        
        注意：此方法是幂等的，多次调用只会执行一次
        """
        if self._initialized and self.adapter:
            return
        
        try:
            if self.is_duckdb:
                self._initialize_duckdb_domains()
            else:
                self.adapter = DatabaseAdapterFactory.create(
                    self.config,
                    is_verbose=self.is_verbose,
                )
                self.domain_adapters = {}
            
            self._initialized = True
            self._log_initialized()
                
        except Exception as e:
            logger.error(f"❌ 数据库连接初始化失败: {e}")
            raise

    def _initialize_duckdb_domains(self) -> None:
        duck_cfg = dict(self.config.get("duckdb") or {})
        domains_cfg = dict(duck_cfg.get("domains") or {})
        shared = {k: v for k, v in duck_cfg.items() if k != "domains"}

        self.domain_adapters = {}
        for domain in sorted(STORAGE_DOMAINS):
            domain_raw = domains_cfg.get(domain)
            if not domain_raw:
                raise ValueError(f"DuckDB 配置缺少域: {domain}")
            merged = {**shared, **domain_raw}
            self.domain_adapters[domain] = (
                DatabaseAdapterFactory.create_duckdb_domain_adapter(
                    merged, is_verbose=self.is_verbose
                )
            )

        self.adapter = self.domain_adapters.get(PRIMARY_DUCKDB_DOMAIN)
        if self.adapter is None:
            raise RuntimeError("DuckDB 主域 data 适配器未创建")

    def _resolve_adapter(self, domain: Optional[str] = None) -> BaseDatabaseAdapter:
        """解析目标适配器；DuckDB 默认 data 域。"""
        if not self._initialized:
            self.initialize()
        if not self.is_duckdb:
            if not self.adapter:
                raise RuntimeError("数据库未初始化")
            return self.adapter
        d = str(domain or PRIMARY_DUCKDB_DOMAIN).lower()
        adapter = self.domain_adapters.get(d)
        if adapter is None:
            raise KeyError(f"未知 DuckDB 存储域: {domain!r}")
        return adapter

    def adapter_for_domain(self, domain: str) -> BaseDatabaseAdapter:
        """按存储域获取适配器；非 DuckDB 时始终返回主适配器。"""
        return self._resolve_adapter(domain)

    def _log_initialized(self) -> None:
        database_type = self.database_type
        if database_type == "postgresql":
            pg_config = self.config.get("postgresql", {})
            logger.debug(
                "✅ 数据库连接已建立（PostgreSQL: %s）",
                pg_config.get("database", "unknown"),
            )
        elif database_type == "mysql":
            mysql_config = self.config.get("mysql", {})
            logger.debug(
                "✅ 数据库连接已建立（MySQL: %s）",
                mysql_config.get("database", "unknown"),
            )
        elif database_type == "duckdb":
            paths = {
                d: (a.config.get("db_path") if hasattr(a, "config") else "?")
                for d, a in self.domain_adapters.items()
            }
            logger.debug("✅ DuckDB 多域连接已建立: %s", paths)
    
    @contextmanager
    def get_connection(self, domain: Optional[str] = None):
        """
        获取数据库连接（上下文管理器）
        
        Args:
            domain: DuckDB 存储域；省略时使用主域（data）
        """
        adapter = self._resolve_adapter(domain)
        
        conn = adapter.get_connection()
        try:
            yield conn
        finally:
            if hasattr(adapter, "_put_connection"):
                if hasattr(conn, "pg_conn"):
                    adapter._put_connection(conn.pg_conn)
                elif hasattr(conn, "mysql_conn"):
                    adapter._put_connection(conn.mysql_conn)
                else:
                    adapter._put_connection(conn)
    
    @contextmanager
    def transaction(self, domain: Optional[str] = None):
        """事务上下文管理器；DuckDB 可指定域。"""
        adapter = self._resolve_adapter(domain)
        with adapter.transaction() as cursor:
            yield cursor
    
    @contextmanager
    def get_sync_cursor(self, domain: Optional[str] = None):
        """获取数据库游标；DuckDB 可指定域。"""
        adapter = self._resolve_adapter(domain)
        
        cursor = DatabaseCursor(adapter)
        try:
            yield cursor
        except Exception as e:
            logger.error(f"Database operation failed: {e}")
            raise
        finally:
            cursor.close()
    
    def execute_sync_query(
        self, query: str, params: Any = None, domain: Optional[str] = None
    ):
        """执行同步查询；DuckDB 可指定域。"""
        return self._resolve_adapter(domain).execute_query(query, params)
    
    def close(self):
        """关闭数据库连接"""
        if self.domain_adapters:
            for adapter in self.domain_adapters.values():
                if adapter:
                    adapter.close()
            self.domain_adapters = {}
        elif self.adapter:
            self.adapter.close()
        self.adapter = None
        self._initialized = False
        if self.is_verbose:
            logger.info("✅ 数据库连接已关闭")
    
    @property
    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized
