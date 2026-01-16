"""
ConnectionManager - 连接和事务管理

职责：
- 数据库适配器创建和初始化
- 连接获取和释放
- 事务管理
- 游标管理
"""
from typing import Optional, Dict, Any
from contextlib import contextmanager
from loguru import logger

from core.infra.db.table_queryers.adapters.factory import DatabaseAdapterFactory
from core.infra.db.table_queryers.adapters.base_adapter import BaseDatabaseAdapter
from core.infra.db.helpers.db_helpers import DatabaseCursor


class ConnectionManager:
    """
    连接和事务管理器
    
    职责：
    - 数据库适配器创建和初始化
    - 连接获取和释放
    - 事务管理
    - 游标管理
    """
    
    def __init__(self, config: Dict, is_verbose: bool = False, read_only: bool = False):
        """
        初始化连接管理器
        
        Args:
            config: 数据库配置
            is_verbose: 是否输出详细日志
            read_only: 是否以只读模式打开
        """
        self.config = config
        self.is_verbose = is_verbose
        self.read_only = read_only
        self.adapter: Optional[BaseDatabaseAdapter] = None
        self._initialized = False
    
    def initialize(self):
        """
        初始化数据库连接
        
        步骤：
        1. 使用适配器工厂创建适配器
        2. 连接数据库
        """
        try:
            # 创建适配器
            self.adapter = DatabaseAdapterFactory.create(
                self.config,
                is_verbose=self.is_verbose,
                read_only=self.read_only
            )
            
            self._initialized = True
            
            # 显示初始化信息
            database_type = self.config.get('database_type', 'postgresql')
            if self.is_verbose:
                if database_type == 'postgresql':
                    pg_config = self.config.get('postgresql', {})
                    logger.info(f"✅ 数据库连接已建立（PostgreSQL: {pg_config.get('database', 'unknown')}）")
                elif database_type == 'mysql':
                    mysql_config = self.config.get('mysql', {})
                    logger.info(f"✅ 数据库连接已建立（MySQL: {mysql_config.get('database', 'unknown')}）")
                elif database_type == 'sqlite':
                    sqlite_config = self.config.get('sqlite', {})
                    db_path = sqlite_config.get('db_path', 'unknown')
                    logger.info(f"✅ 数据库连接已建立（SQLite: {db_path}）")
                
        except Exception as e:
            logger.error(f"❌ 数据库连接初始化失败: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """
        获取数据库连接（上下文管理器）
        
        使用方式:
            with connection_manager.get_connection() as conn:
                # 连接对象可以直接执行 SQL
                conn.execute("SELECT ...")
        """
        if not self.adapter:
            raise RuntimeError("数据库未初始化，请先调用 initialize()")
        
        conn = self.adapter.get_connection()
        try:
            yield conn
        finally:
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
            with connection_manager.transaction() as cursor:
                cursor.execute("UPDATE ...")
                cursor.execute("INSERT ...")
                # 自动提交，出错自动回滚
        """
        if not self.adapter:
            raise RuntimeError("数据库未初始化，请先调用 initialize()")
        
        # 使用适配器的事务管理器
        with self.adapter.transaction() as cursor:
            yield cursor
    
    @contextmanager
    def get_sync_cursor(self):
        """
        获取数据库游标的上下文管理器
        
        使用方式:
            with connection_manager.get_sync_cursor() as cursor:
                cursor.execute("SELECT * FROM table")
                results = cursor.fetchall()
        """
        if not self._initialized or not self.adapter:
            raise RuntimeError("ConnectionManager not initialized. Call initialize() first.")
        
        cursor = DatabaseCursor(self.adapter)
        try:
            yield cursor
        except Exception as e:
            logger.error(f"Database operation failed: {e}")
            raise
        finally:
            cursor.close()
    
    def execute_sync_query(self, query: str, params: Any = None):
        """
        执行同步查询语句
        
        Args:
            query: SQL 查询语句（使用 %s 占位符，适配器会自动转换）
            params: 查询参数
            
        Returns:
            查询结果列表（字典格式）
        """
        if not self.adapter:
            raise RuntimeError("ConnectionManager not initialized. Call initialize() first.")
        
        # 使用适配器的 execute_query 方法（会自动处理占位符转换）
        return self.adapter.execute_query(query, params)
    
    def close(self):
        """关闭数据库连接"""
        if self.adapter:
            self.adapter.close()
            self.adapter = None
            self._initialized = False
            if self.is_verbose:
                logger.info("✅ 数据库连接已关闭")
    
    @property
    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized
