"""
DatabaseManager - 数据库管理器（支持多种数据库后端）

- 使用适配器模式支持 PostgreSQL、MySQL、SQLite
- 使用 DbSchemaManager 管理表结构
- 提供简洁的 CRUD 接口
"""
from typing import Optional, Dict, List, Any, Callable
from contextlib import contextmanager
from pathlib import Path
from loguru import logger
from datetime import datetime, date

from app.core.conf.db_conf import DB_CONF
from app.core.infra.db.batch_write_queue import BatchWriteQueue
from app.core.infra.db.adapters.factory import DatabaseAdapterFactory
from app.core.infra.db.adapters.base_adapter import BaseDatabaseAdapter
from .db_schema_manager import DbSchemaManager


class DatabaseCursor:
    """
    通用数据库游标包装类
    
    兼容不同数据库的游标接口，统一返回字典格式的结果。
    """
    def __init__(self, adapter: BaseDatabaseAdapter):
        self.adapter = adapter
        self._cursor = None
        self._result = None
    
    def execute(self, query: str, params: Any = None):
        """执行 SQL 查询"""
        # 使用适配器的事务管理器获取游标
        # 注意：这里需要适配器支持游标访问
        # 对于 PostgreSQL，使用 transaction() 获取游标
        # 对于 DuckDB，使用 get_connection() 获取连接
        self._query = query
        self._params = params
        return self
    
    def fetchall(self) -> List[Dict[str, Any]]:
        """获取所有结果，转换为字典列表"""
        if not hasattr(self, '_query'):
            return []
        
        # 使用适配器的 execute_query 方法
        return self.adapter.execute_query(self._query, self._params)
    
    def fetchone(self) -> Optional[Dict[str, Any]]:
        """获取一条结果"""
        results = self.fetchall()
        return results[0] if results else None
    
    @property
    def rowcount(self) -> int:
        """返回影响的行数"""
        if self._result:
            return len(self._result)
        return 0
    
    def close(self):
        """关闭游标"""
        pass


class DatabaseManager:
    """
    数据库管理器（支持多种数据库后端）
    
    职责：
    - 数据库连接管理（通过适配器）
    - 基础 CRUD 操作
    - 事务管理
    - 提供默认实例（支持多进程自动初始化）
    
    不再负责：
    - Schema 解析和建表（由 SchemaManager 负责）
    - 表模型缓存（归 DataManager）
    - 具体数据库实现（由适配器负责）
    """
    
    _default_instance = None  # 默认实例（支持多进程）
    _auto_init_enabled = True  # 是否启用自动初始化
    
    def __init__(self, config: Dict = None, is_verbose: bool = False, read_only: bool = False):
        """
        初始化数据库管理器
        
        Args:
            config: 数据库配置（默认使用 DB_CONF）
                - 如果提供旧格式（只有 db_path），自动转换为新格式
                - 新格式应包含 database_type 和对应的数据库配置
            is_verbose: 是否输出详细日志
            read_only: 是否以只读模式打开（多进程读取场景使用，仅 SQLite 支持）
        """
        # 加载配置
        if config is None:
            config = DB_CONF
        
        # 如果是旧格式配置，转换为新格式
        if 'database_type' not in config:
            if 'db_path' in config:
                # 旧格式：只有 db_path，转换为 SQLite
                self.config = {
                    'database_type': 'sqlite',
                    'sqlite': config,
                    'batch_write': config.get('batch_write', {
                        'batch_size': 1000,
                        'flush_interval': 5.0,
                        'enable': True
                    })
                }
            elif 'host' in config and 'database' in config:
                # 旧格式：host + database，根据端口判断
                port = config.get('port', 3306)
                db_type = 'mysql' if port != 5432 else 'postgresql'
                self.config = {
                    'database_type': db_type,
                    db_type: config,
                    'batch_write': config.get('batch_write', {
                        'batch_size': 1000,
                        'flush_interval': 5.0,
                        'enable': True
                    })
                }
            else:
                self.config = config
        else:
            self.config = config
        
        self.is_verbose = is_verbose
        self.read_only = read_only
        self.adapter: Optional[BaseDatabaseAdapter] = None
        self._initialized = False
        
        # Schema 管理器（传入数据库类型，用于生成对应的 SQL）
        database_type = self.config.get('database_type', 'postgresql')
        self.schema_manager = DbSchemaManager(
            is_verbose=is_verbose,
            database_type=database_type
        )
        
        # 批量写入队列（延迟初始化，在 initialize 后创建）
        self._write_queue: Optional[BatchWriteQueue] = None
    
    @classmethod
    def set_default(cls, instance: 'DatabaseManager'):
        """
        设置默认的 DatabaseManager 实例
        
        Args:
            instance: DatabaseManager 实例
        """
        cls._default_instance = instance
        if instance.is_verbose:
            logger.info("✅ DatabaseManager 已设置为默认实例")
    
    @classmethod
    def get_default(cls, auto_init: bool = True) -> 'DatabaseManager':
        """
        获取默认的 DatabaseManager 实例
        
        多进程安全：
        - 如果实例不存在（多进程场景下 context 丢失）
        - 会自动创建并初始化新实例
        - 如果检测到是子进程，自动使用只读模式（避免写锁冲突）
        
        Args:
            auto_init: 是否自动初始化（默认 True）
        
        Returns:
            DatabaseManager 实例
        """
        if cls._default_instance is None:
            if auto_init and cls._auto_init_enabled:
                # 检测是否是子进程（多进程场景）
                import multiprocessing
                is_child_process = multiprocessing.current_process().name != 'MainProcess'
                
                # 自动创建并初始化（多进程场景）
                if is_child_process:
                    logger.info("🔄 检测到子进程环境，自动创建只读 DatabaseManager 实例（避免写锁冲突）")
                    instance = cls(is_verbose=False, read_only=True)
                else:
                    logger.info("🔄 检测到 DatabaseManager 未初始化，自动创建实例")
                    instance = cls(is_verbose=False)
                instance.initialize()
                cls._default_instance = instance
                logger.info("✅ DatabaseManager 自动初始化完成")
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
            if hasattr(cls._default_instance, 'adapter') and cls._default_instance.adapter:
                cls._default_instance.adapter.close()
        cls._default_instance = None
        # logger.info("🔄 DatabaseManager 默认实例已重置")
    
    def initialize(self):
        """
        初始化数据库管理器
        
        步骤：
        1. 使用适配器工厂创建适配器
        2. 连接数据库
        3. 初始化批量写入队列（如果需要）
        
        注意：不再创建表，表的创建由 DataManager 负责
        """
        try:
            # 1. 创建适配器
            self.adapter = DatabaseAdapterFactory.create(
                self.config,
                is_verbose=self.is_verbose,
                read_only=self.read_only
            )
            
            # 更新 Schema 管理器的数据库类型（如果初始化时还不知道）
            database_type = self.config.get('database_type', 'postgresql')
            self.schema_manager.database_type = database_type
            
            self._initialized = True
            
            # 2. 初始化批量写入队列（只读模式下跳过）
            if not self.read_only:
                self._init_write_queue()
            elif self.is_verbose:
                logger.info("ℹ️  只读模式，跳过批量写入队列初始化")
            
            # 3. 显示初始化信息
            database_type = self.config.get('database_type', 'postgresql')
            if self.is_verbose:
                if database_type == 'postgresql':
                    pg_config = self.config.get('postgresql', {})
                    logger.info(f"✅ DatabaseManager 初始化完成（PostgreSQL: {pg_config.get('database', 'unknown')}）")
                elif database_type == 'mysql':
                    mysql_config = self.config.get('mysql', {})
                    logger.info(f"✅ DatabaseManager 初始化完成（MySQL: {mysql_config.get('database', 'unknown')}）")
                elif database_type == 'sqlite':
                    sqlite_config = self.config.get('sqlite', {})
                    db_path = sqlite_config.get('db_path', 'unknown')
                    logger.info(f"✅ DatabaseManager 初始化完成（SQLite: {db_path}）")
                
        except Exception as e:
            logger.error(f"❌ DatabaseManager 初始化失败: {e}")
            raise
    
    def _init_write_queue(self):
        """初始化批量写入队列"""
        try:
            from .batch_write_queue import BatchWriteQueue
            
            # 从配置读取批量写入参数
            batch_config = self.config.get('batch_write', {})
            batch_size = batch_config.get('batch_size', 1000)
            flush_interval = batch_config.get('flush_interval', 5.0)
            enable = batch_config.get('enable', True)
            
            self._write_queue = BatchWriteQueue(
                db_manager=self,
                batch_size=batch_size,
                flush_interval=flush_interval,
                enable=enable
            )
            
            if self.is_verbose and enable:
                logger.info(f"✅ 批量写入队列已启用 (batch_size={batch_size}, flush_interval={flush_interval}s)")
            elif not enable and self.is_verbose:
                logger.info("ℹ️  批量写入队列已禁用（直接写入模式）")
        except Exception as e:
            logger.warning(f"⚠️ 初始化批量写入队列失败: {e}，将使用直接写入模式")
            self._write_queue = None
    
    # ==================== 连接管理 ====================
    
    @contextmanager
    def get_connection(self):
        """
        获取数据库连接（上下文管理器）
        
        使用方式:
            with db.get_connection() as conn:
                # 连接对象可以直接执行 SQL（兼容 DuckDB 和 PostgreSQL）
                conn.execute("SELECT ...")
        """
        if not self.adapter:
            raise RuntimeError("数据库未初始化，请先调用 initialize()")
        
        conn = self.adapter.get_connection()
        try:
            yield conn
        finally:
            # PostgreSQL 需要归还连接，SQLite/MySQL 不需要
            if hasattr(self.adapter, '_put_connection'):
                # 如果是包装对象，获取原始连接
                if hasattr(conn, 'pg_conn'):
                    self.adapter._put_connection(conn.pg_conn)
                else:
                    self.adapter._put_connection(conn)
    
    @contextmanager
    def transaction(self):
        """
        事务上下文管理器
        
        使用方式:
            with db.transaction() as cursor:
                cursor.execute("INSERT ...")
                cursor.execute("UPDATE ...")
                # 自动提交或回滚
        """
        if not self.adapter:
            raise RuntimeError("数据库未初始化，请先调用 initialize()")
        
        # 使用适配器的事务管理器
        with self.adapter.transaction() as cursor:
            yield cursor
    
    # ==================== 表管理（委托给 SchemaManager）====================
    
    def register_table(self, table_name: str, schema: Dict):
        """
        注册自定义表（给策略用）
        
        Args:
            table_name: 表名
            schema: 表的 schema 定义
        """
        self.schema_manager.register_table(table_name, schema)
        
        if self._initialized:
            # 如果已经初始化，立即创建表
            self.schema_manager.create_table_with_indexes(schema, self.get_connection)
    
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
        if not self.adapter:
            raise RuntimeError("数据库未初始化，请先调用 initialize()")
        
        return self.adapter.is_table_exists(table_name)
    
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
    
    # ==================== 工具方法 ====================
    
    def close(self):
        """关闭数据库连接"""
        if self.adapter:
            self.adapter.close()
            self.adapter = None
            self._initialized = False
            if self.is_verbose:
                logger.info("✅ 数据库连接已关闭")
    
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
        elif database_type == 'sqlite':
            sqlite_config = self.config.get('sqlite', {})
            stats.update({
                'db_path': str(sqlite_config.get('db_path', '')),
                'timeout': sqlite_config.get('timeout', 5.0),
            })
        
        return stats
    
    @contextmanager
    def get_sync_cursor(self):
        """
        获取数据库游标的上下文管理器
        
        使用方式:
            with db.get_sync_cursor() as cursor:
                cursor.execute("SELECT * FROM table")
                results = cursor.fetchall()
        """
        if not self._initialized or not self.adapter:
            raise RuntimeError("DatabaseManager not initialized. Call initialize() first.")
        
        cursor = DatabaseCursor(self.adapter)
        try:
            yield cursor
        except Exception as e:
            logger.error(f"Database operation failed: {e}")
            raise
        finally:
            cursor.close()
    
    def execute_sync_query(self, query: str, params: Any = None) -> List[Dict[str, Any]]:
        """
        执行同步查询语句
        
        Args:
            query: SQL 查询语句（使用 %s 占位符，适配器会自动转换）
            params: 查询参数
            
        Returns:
            查询结果列表（字典格式）
        """
        if not self.adapter:
            raise RuntimeError("DatabaseManager not initialized. Call initialize() first.")
        
        # 使用适配器的 execute_query 方法（会自动处理占位符转换）
        return self.adapter.execute_query(query, params)
    
    def queue_write(self, table_name: str, data_list: List[Dict], unique_keys: List[str], callback: Callable = None):
        """
        队列写入（使用批量写入队列，解决并发写入问题）
        
        Args:
            table_name: 表名
            data_list: 数据列表
            unique_keys: 唯一键
            callback: 回调函数
        """
        if not data_list:
            return
        
        # 如果批量写入队列可用且启用，使用队列
        if self._write_queue and self._write_queue.enable:
            self._write_queue.enqueue(table_name, data_list, unique_keys, callback)
        else:
            # 否则直接写入（单线程场景或队列未启用）
            self._direct_write(table_name, data_list, unique_keys, callback)
    
    def _direct_write(
        self,
        table_name: str,
        data_list: List[Dict],
        unique_keys: List[str],
        callback: Callable = None
    ):
        """
        直接写入（不使用队列，单线程场景使用）
        
        注意：此方法不是线程安全的，多线程场景应使用 queue_write
        
        Args:
            table_name: 表名
            data_list: 数据列表
            unique_keys: 唯一键列表（如果为空，使用纯 INSERT；否则使用 INSERT ... ON CONFLICT）
            callback: 回调函数
        """
        try:
            from .db_base_model import DBService
            
            if not data_list:
                return
            
            if not unique_keys:
                # 纯 INSERT（不需要去重）
                columns, placeholders = DBService.to_columns_and_values(data_list)
                columns_sql = ', '.join(columns)
                values = [tuple(data[col] for col in columns) for data in data_list]
            else:
                # 使用 INSERT ... ON CONFLICT DO UPDATE（PostgreSQL/SQLite 风格 Upsert）
                columns, values, update_clause = DBService.to_upsert_params(data_list, unique_keys)
                
                if not columns:
                    return
                
                columns_sql = ', '.join(columns)
                conflict_cols = ', '.join(unique_keys)
            
            if not self.adapter:
                raise RuntimeError("DatabaseManager not initialized.")
            
            # 使用适配器的 execute_batch 方法进行批量插入
            # 构建 INSERT SQL
            placeholder = self.adapter.get_placeholder()
            placeholders = ', '.join([placeholder] * len(columns))
            
            if not unique_keys:
                # 纯 INSERT
                insert_sql = f"INSERT INTO {table_name} ({columns_sql}) VALUES ({placeholders})"
                # 使用 execute_batch
                self.adapter.execute_batch(insert_sql, values)
            else:
                # INSERT ... ON CONFLICT
                if update_clause:
                    insert_sql = (
                        f"INSERT INTO {table_name} ({columns_sql}) VALUES ({placeholders}) "
                        f"ON CONFLICT ({conflict_cols}) DO UPDATE SET {update_clause}"
                    )
                else:
                    insert_sql = (
                        f"INSERT INTO {table_name} ({columns_sql}) VALUES ({placeholders}) "
                        f"ON CONFLICT ({conflict_cols}) DO NOTHING"
                    )
                # 使用 execute_batch
                self.adapter.execute_batch(insert_sql, values)
            
            if callback:
                callback(table_name, len(data_list))
                    
        except Exception as e:
            logger.error(f"Failed to write to {table_name}: {e}")
            raise
    
    def flush_writes(self, table_name: Optional[str] = None):
        """
        立即刷新指定表或所有表的待写入数据
        
        Args:
            table_name: 表名，None 表示刷新所有表
        """
        if self._write_queue:
            self._write_queue.flush(table_name)
    
    def get_write_stats(self) -> Dict[str, Any]:
        """获取写入统计信息"""
        if self._write_queue:
            return self._write_queue.get_stats()
        return {}
    
    def wait_for_writes(self, timeout: float = 30.0):
        """
        等待所有写入完成
        
        Args:
            timeout: 超时时间（秒）
        """
        if self._write_queue:
            self._write_queue.wait_for_writes(timeout)
    
    def close(self):
        """关闭数据库连接和写入队列"""
        # 关闭写入队列（会刷新所有待写入数据）
        if self._write_queue:
            self._write_queue.shutdown()
            self._write_queue = None
        
        # 关闭数据库连接（通过适配器）
        if self.adapter:
            try:
                self.adapter.close()
            except:
                pass
            self.adapter = None
        
        self._initialized = False
    
    def __del__(self):
        """析构函数：确保连接和队列关闭"""
        try:
            self.close()
        except:
            pass
