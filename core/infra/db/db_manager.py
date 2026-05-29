"""
DatabaseManager - 数据库管理器（支持多种数据库后端）

三层架构：
- ConnectionManager: 连接和事务管理
- SchemaManager: Schema 管理和表初始化
- TableManager: 表操作 API

对外暴露统一接口，内部使用三个管理器协同工作。
"""
from typing import Optional, Dict, List, Any, Callable
from contextlib import contextmanager
from pathlib import Path
import logging

from core.infra.project_context import ConfigManager
from core.infra.db.connection_management.connection_manager import ConnectionManager
from core.infra.db.schema_management.schema_manager import SchemaManager
from core.infra.db.table_management.table_manager import TableManager
from core.infra.db.helpers.db_helpers import DBHelper
from core.infra.db.storage_registry import StorageRegistry, PRIMARY_DUCKDB_DOMAIN


logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    数据库管理器（支持多种数据库后端）
    
    三层架构：
    - ConnectionManager: 连接和事务管理
    - SchemaManager: Schema 管理和表初始化
    - TableManager: 表操作 API
    
    对外暴露统一接口，内部使用三个管理器协同工作。
    """
    
    _default_instance = None  # 默认实例（支持多进程）
    _auto_init_enabled = True  # 是否启用自动初始化
    
    def __init__(self, config: Dict = None, is_verbose: bool = False):
        """
        初始化数据库管理器
        
        Args:
            config: 数据库配置（默认使用 ConfigManager.load_database_config()）
                - 如果为 None，从 ConfigManager 加载配置
                - 配置必须包含 database_type 和对应的数据库配置
            is_verbose: 是否输出详细日志
        """
        # 加载配置
        if config is None:
            config = ConfigManager.load_database_config()
        
        # 解析和验证配置
        self.config = DBHelper.parse_database_config(config)
        
        self.is_verbose = is_verbose
        self._initialized = False

        database_type = self.config.get("database_type", "postgresql")
        self.storage_registry = StorageRegistry(database_type)
        
        # 初始化三个管理器
        
        # 1. ConnectionManager - 连接和事务管理
        self.connection_manager = ConnectionManager(
            config=self.config,
            is_verbose=is_verbose,
        )
        
        # 2. SchemaManager - Schema 管理和表初始化
        self.schema_manager = SchemaManager(
            is_verbose=is_verbose,
            database_type=database_type,
        )
        
        # 3. TableManager - 表操作 API（延迟初始化，需要 adapter）
        self.table_manager: Optional[TableManager] = None
    
    @classmethod
    def set_default(cls, instance: 'DatabaseManager'):
        """
        设置默认的 DatabaseManager 实例
        
        Args:
            instance: DatabaseManager 实例
        """
        cls._default_instance = instance
        logger.debug("✅ DatabaseManager 已设置为默认实例")
    
    @classmethod
    def get_default(cls, auto_init: bool = True) -> 'DatabaseManager':
        """
        获取默认的 DatabaseManager 实例
        
        多进程安全：
        - 如果实例不存在（多进程场景下 context 丢失）
        - 会自动创建并初始化新实例
        
        Args:
            auto_init: 是否自动初始化（默认 True）
        
        Returns:
            DatabaseManager 实例
        """
        if cls._default_instance is None:
            if auto_init and cls._auto_init_enabled:
                # 使用锁确保多进程/多线程安全
                import threading
                if not hasattr(cls, '_init_lock'):
                    cls._init_lock = threading.Lock()
                
                with cls._init_lock:
                    # 双重检查，避免重复初始化
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
        """
        重置默认实例
        
        使用场景：
        - 测试时清理状态
        - 切换数据库配置
        """
        if cls._default_instance is not None:
            # 关闭连接
            if hasattr(cls._default_instance, 'connection_manager'):
                cls._default_instance.connection_manager.close()
        cls._default_instance = None
    
    def initialize(self):
        """
        初始化数据库管理器
        
        步骤：
        1. 初始化 ConnectionManager（创建适配器和连接）
        2. 初始化 TableManager（需要 adapter）
        3. 初始化批量写入队列（如果需要）
        """
        try:
            # 1. 初始化 ConnectionManager
            self.connection_manager.initialize()
            
            # 更新 SchemaManager 的数据库类型
            database_type = self.config.get('database_type', 'postgresql')
            self.schema_manager.database_type = database_type
            
            # 2. 初始化 TableManager（需要 adapter）
            self.table_manager = TableManager(
                adapter=self.connection_manager.adapter,
                config=self.config,
            )
            
            # 3. 构建表 → 存储域映射（DuckDB 路由依赖）
            self.rebuild_storage_registry()

            # 4. 批量写入队列延迟初始化（只在需要写入时才初始化）
            # 注意：枚举器等只读场景不需要初始化写入队列，可以节省资源
            # 写入队列会在第一次调用 queue_write() 时自动初始化
            
            self._initialized = True
            
            # 显示初始化信息（使用 debug 级别，避免在默认 INFO 下过于啰嗦）
            database_type = self.config.get('database_type', 'postgresql')
            if database_type == 'postgresql':
                pg_config = self.config.get('postgresql', {})
                logger.debug(f"✅ DatabaseManager 初始化完成（PostgreSQL: {pg_config.get('database', 'unknown')}）")
            elif database_type == 'mysql':
                mysql_config = self.config.get('mysql', {})
                logger.debug(f"✅ DatabaseManager 初始化完成（MySQL: {mysql_config.get('database', 'unknown')}）")
            elif database_type == 'duckdb':
                n = len(self.storage_registry.table_to_domain)
                logger.debug(
                    "✅ DatabaseManager 初始化完成（DuckDB 三域，已注册 %s 张表）",
                    n,
                )
                
        except Exception as e:
            logger.error(f"❌ DatabaseManager 初始化失败: {e}")
            raise
    
    # ==================== ConnectionManager 委托方法 ====================
    
    @property
    def database_type(self) -> str:
        """当前进程缓存的数据库类型（mysql | postgresql | duckdb）。"""
        return str(self.config.get("database_type", "postgresql")).lower()

    @property
    def is_duckdb(self) -> bool:
        return self.storage_registry.is_duckdb

    @property
    def adapter(self):
        """主适配器（DuckDB 为 data 域）。"""
        return self.connection_manager.adapter

    def adapter_for_table(self, table_name: str):
        """按表 storage_domain 解析适配器。"""
        if self.is_duckdb:
            return self.connection_manager.adapter_for_domain(
                self.storage_registry.get_domain(table_name)
            )
        return self.adapter

    def get_table_domain(self, table_name: str) -> str:
        """查询表所属 storage_domain。"""
        return self.storage_registry.get_domain(table_name)

    def rebuild_storage_registry(self) -> None:
        """从 core/tables 重新加载 schema 并刷新表→域映射。"""
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
        """获取数据库连接（委托给 ConnectionManager）"""
        with self.connection_manager.get_connection() as conn:
            yield conn
    
    @contextmanager
    def transaction(self):
        """事务上下文管理器（委托给 ConnectionManager）"""
        with self.connection_manager.transaction() as cursor:
            yield cursor
    
    @contextmanager
    def get_sync_cursor(self, domain: Optional[str] = None):
        """获取数据库游标（委托给 ConnectionManager）"""
        with self.connection_manager.get_sync_cursor(domain=domain) as cursor:
            yield cursor

    @contextmanager
    def get_sync_cursor_for_table(self, table_name: str):
        """按表 storage_domain 获取游标。"""
        domain = self.get_table_domain(table_name) if self.is_duckdb else None
        with self.connection_manager.get_sync_cursor(domain=domain) as cursor:
            yield cursor

    def connection_factory_for_table(self, table_name: str) -> Callable:
        """SchemaManager 建表用的连接工厂（按表路由域）。"""
        domain = self.get_table_domain(table_name) if self.is_duckdb else None

        @contextmanager
        def get_connection_func():
            with self.connection_manager.get_connection(domain=domain) as conn:
                yield conn

        return get_connection_func
    
    def execute_sync_query(
        self, query: str, params: Any = None, domain: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """执行同步查询（委托给 ConnectionManager）"""
        return self.connection_manager.execute_sync_query(query, params, domain=domain)

    def execute_sync_query_for_table(
        self, table_name: str, query: str, params: Any = None
    ) -> List[Dict[str, Any]]:
        """按表名路由域后执行查询。"""
        d = self.get_table_domain(table_name) if self.is_duckdb else None
        return self.execute_sync_query(query, params, domain=d)
    
    # ==================== SchemaManager 委托方法 ====================
    
    def register_table(self, table_name: str, schema: Dict):
        """
        注册自定义表（给策略用）
        
        Args:
            table_name: 表名
            schema: 表的 schema 定义
        """
        self.schema_manager.register_table(table_name, schema)
        self.storage_registry.register_schema(schema)
        
        if self._initialized:
            self.schema_manager.create_table_with_indexes(
                schema, self.connection_factory_for_table(table_name)
            )
    
    def create_registered_tables(self):
        """创建所有注册的表（策略表）"""
        self.schema_manager.create_registered_tables(self.get_connection)
    
    def is_table_exists(self, table_name: str) -> bool:
        """
        检查表是否存在
        
        Args:
            table_name: 表名
            
        Returns:
            是否存在
        """
        if not self._initialized:
            raise RuntimeError("数据库未初始化，请先调用 initialize()")
        
        return self.schema_manager.is_table_exists(
            table_name, self.adapter_for_table(table_name)
        )

    def create_all_base_tables(self) -> None:
        """
        创建 core/tables 下所有基表。

        DuckDB 按 storage_domain 写入对应 .duckdb 文件；其它后端单库创建。
        """
        schemas = self.schema_manager.load_all_schemas()
        for table_name, schema in schemas.items():
            self.storage_registry.register_schema(schema)
            try:
                self.schema_manager.create_table_with_indexes(
                    schema, self.connection_factory_for_table(table_name)
                )
            except Exception as e:
                logger.error("❌ 创建表失败 '%s': %s", table_name, e)
    
    def get_table_schema(self, table_name: str) -> Optional[Dict]:
        """
        获取表的 schema
        
        Args:
            table_name: 表名
            
        Returns:
            schema 字典，不存在返回 None
        """
        return self.schema_manager.get_table_schema(table_name)
    
    def get_table_fields(self, table_name: str) -> List[str]:
        """
        获取表的所有字段名
        
        Args:
            table_name: 表名
            
        Returns:
            字段名列表
        """
        return self.schema_manager.get_table_fields(table_name)
    
    # ==================== TableManager 委托方法 ====================
    
    def queue_write(
        self,
        table_name: str,
        data_list: List[Dict],
        unique_keys: List[str],
        callback: Callable = None
    ):
        """
        队列写入（委托给 TableManager）
        
        Args:
            table_name: 表名
            data_list: 数据列表
            unique_keys: 唯一键
            callback: 回调函数
        """
        if not self.table_manager:
            raise RuntimeError("TableManager not initialized. Call initialize() first.")
        self.table_manager.queue_write(table_name, data_list, unique_keys, callback)
    
    def flush_writes(self, table_name: Optional[str] = None):
        """
        立即刷新指定表或所有表的待写入数据（委托给 TableManager）
        
        Args:
            table_name: 表名，None 表示刷新所有表
        """
        if self.table_manager:
            self.table_manager.flush_writes(table_name)
    
    def get_write_stats(self) -> Dict[str, Any]:
        """获取写入统计信息（委托给 TableManager）"""
        if self.table_manager:
            return self.table_manager.get_write_stats()
        return {}
    
    def wait_for_writes(self, timeout: float = 30.0):
        """
        等待所有写入完成（委托给 TableManager）
        
        Args:
            timeout: 超时时间（秒）
        """
        if self.table_manager:
            self.table_manager.wait_for_writes(timeout)
    
    # ==================== 工具方法 ====================
    
    def close(self):
        """关闭数据库连接和写入队列"""
        # 关闭 TableManager（会关闭写入队列）
        if self.table_manager:
            self.table_manager.close()
        
        # 关闭 ConnectionManager（会关闭数据库连接）
        if self.connection_manager:
            self.connection_manager.close()
        
        self._initialized = False
    
    def get_stats(self) -> Dict:
        """
        获取数据库统计信息
        
        Returns:
            统计信息字典
        """
        database_type = self.config.get('database_type', 'postgresql')
        stats = {
            'initialized': self._initialized,
            'database_type': database_type,
        }
        
        if database_type == 'postgresql':
            pg_config = self.config.get('postgresql', {})
            stats.update({
                'host': pg_config.get('host', ''),
                'port': pg_config.get('port', 5432),
                'database': pg_config.get('database', ''),
            })
        elif database_type == 'mysql':
            mysql_config = self.config.get('mysql', {})
            stats.update({
                'host': mysql_config.get('host', ''),
                'port': mysql_config.get('port', 3306),
                'database': mysql_config.get('database', ''),
            })
        elif database_type == 'duckdb':
            duck = self.config.get('duckdb', {})
            stats['duckdb_domains'] = {
                d: (a.config.get('db_path') if getattr(a, 'config', None) else None)
                for d, a in self.connection_manager.domain_adapters.items()
            }
            stats['table_domain_map_size'] = len(self.storage_registry.table_to_domain)

        return stats
    
    def __del__(self):
        """析构函数：确保连接和队列关闭"""
        try:
            self.close()
        except:
            pass
