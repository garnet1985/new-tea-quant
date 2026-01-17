"""
PostgreSQLAdapter - PostgreSQL 数据库适配器

实现 PostgreSQL 数据库的连接和操作。
"""
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor, execute_batch
from typing import Dict, List, Any, Optional
from contextlib import contextmanager
from loguru import logger

from .base_adapter import BaseDatabaseAdapter


class PostgreSQLAdapter(BaseDatabaseAdapter):
    """
    PostgreSQL 数据库适配器
    
    特性：
    - 使用连接池管理连接
    - 支持事务
    - 返回字典格式的结果
    """
    
    def __init__(self, config: Dict[str, Any], is_verbose: bool = False):
        """
        初始化 PostgreSQL 适配器
        
        Args:
            config: PostgreSQL 配置字典
                - host: 主机地址
                - port: 端口
                - database: 数据库名
                - user: 用户名
                - password: 密码
                - pool_size: 连接池大小（可选，默认 10）
            is_verbose: 是否输出详细日志
        """
        self.config = config
        self.is_verbose = is_verbose
        self._connection_pool: Optional[pool.ThreadedConnectionPool] = None
        self._initialized = False
    
    def connect(self, config: Dict[str, Any] = None) -> pool.ThreadedConnectionPool:
        """
        建立 PostgreSQL 连接池
        
        Args:
            config: 数据库配置（如果提供，会覆盖初始化时的配置）
            
        Returns:
            连接池对象
        """
        if config:
            self.config = config
        
        try:
            # 连接池配置
            pool_size = self.config.get('pool_size', 10)
            minconn = self.config.get('pool_minconn', 1)
            maxconn = self.config.get('pool_maxconn', pool_size)
            
            # 创建连接池
            self._connection_pool = pool.ThreadedConnectionPool(
                minconn=minconn,
                maxconn=maxconn,
                host=self.config['host'],
                port=self.config['port'],
                database=self.config['database'],
                user=self.config['user'],
                password=self.config['password']
            )
            
            self._initialized = True
            
            if self.is_verbose:
                logger.info(f"✅ PostgreSQL 连接池创建成功: {self.config['database']} (pool_size={maxconn})")
            
            return self._connection_pool
            
        except Exception as e:
            logger.error(f"❌ PostgreSQL 连接失败: {e}")
            raise
    
    def close(self):
        """关闭连接池"""
        if self._connection_pool:
            self._connection_pool.closeall()
            self._connection_pool = None
            self._initialized = False
            if self.is_verbose:
                logger.info("✅ PostgreSQL 连接池已关闭")
    
    def _get_connection(self):
        """从连接池获取连接"""
        if not self._connection_pool:
            raise RuntimeError("PostgreSQL 适配器未初始化，请先调用 connect()")
        return self._connection_pool.getconn()
    
    def _put_connection(self, conn):
        """将连接归还到连接池"""
        if self._connection_pool:
            self._connection_pool.putconn(conn)
    
    def execute_query(self, query: str, params: Any = None) -> List[Dict[str, Any]]:
        """
        执行查询语句
        
        Args:
            query: SQL 查询语句（使用 %s 占位符，或 ? 会自动转换）
            params: 查询参数
            
        Returns:
            查询结果列表（字典格式）
        """
        conn = None
        try:
            # 标准化查询语句（转换占位符）
            query = self.normalize_query(query)
            
            conn = self._get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                results = cursor.fetchall()
                # RealDictCursor 返回的是 RealDictRow，转换为普通字典
                return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"执行查询失败: {e}\n查询: {query}\n参数: {params}")
            raise
        finally:
            if conn:
                self._put_connection(conn)
    
    def execute_write(self, query: str, params: Any = None) -> int:
        """
        执行写入语句
        
        Args:
            query: SQL 写入语句（使用 %s 占位符，或 ? 会自动转换）
            params: 查询参数
            
        Returns:
            影响的行数
        """
        conn = None
        try:
            # 标准化查询语句（转换占位符）
            query = self.normalize_query(query)
            
            conn = self._get_connection()
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"执行写入失败: {e}\n查询: {query}\n参数: {params}")
            raise
        finally:
            if conn:
                self._put_connection(conn)
    
    def execute_batch(self, query: str, params_list: List[Any]) -> int:
        """
        批量执行写入语句
        
        Args:
            query: SQL 写入语句（使用 %s 占位符，或 ? 会自动转换）
            params_list: 参数列表
            
        Returns:
            总影响的行数
        """
        conn = None
        try:
            # 标准化查询语句（转换占位符）
            query = self.normalize_query(query)
            
            conn = self._get_connection()
            with conn.cursor() as cursor:
                execute_batch(cursor, query, params_list)
                conn.commit()
                return cursor.rowcount * len(params_list)  # 近似值
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"批量写入失败: {e}\n查询: {query}\n记录数: {len(params_list)}")
            raise
        finally:
            if conn:
                self._put_connection(conn)
    
    @contextmanager
    def transaction(self):
        """
        事务上下文管理器
        
        使用方式:
            with adapter.transaction() as cursor:
                cursor.execute("INSERT ...")
                cursor.execute("UPDATE ...")
                # 自动提交或回滚
        """
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                yield cursor
                conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                self._put_connection(conn)
    
    def get_placeholder(self) -> str:
        """返回 PostgreSQL 占位符类型"""
        return '%s'
    
    def get_connection(self):
        """
        获取数据库连接（用于需要直接访问连接的场景）
        
        返回一个包装对象，可以直接执行 SQL：
            conn.execute("SELECT ...")
        
        注意：使用后需要手动归还连接（通过 _put_connection）
        """
        conn = self._get_connection()
        
        # 创建一个包装类，使其可以直接执行 SQL
        class PostgreSQLConnectionWrapper:
            def __init__(self, pg_conn, adapter):
                self.pg_conn = pg_conn
                self.adapter = adapter
            
            def execute(self, query: str, params: Any = None):
                """执行 SQL"""
                with self.pg_conn.cursor() as cursor:
                    cursor.execute(query, params)
                    self.pg_conn.commit()
                return self
            
            def cursor(self):
                """返回游标（用于需要游标的场景）"""
                return self.pg_conn.cursor()
            
            def commit(self):
                """提交事务"""
                self.pg_conn.commit()
            
            def rollback(self):
                """回滚事务"""
                self.pg_conn.rollback()
        
        return PostgreSQLConnectionWrapper(conn, self)
    
    def is_table_exists(self, table_name: str) -> bool:
        """
        检查表是否存在
        
        Args:
            table_name: 表名
            
        Returns:
            是否存在
        """
        query = """
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = %s
        """
        try:
            result = self.execute_query(query, (table_name,))
            return result[0]['count'] > 0 if result else False
        except Exception as e:
            logger.error(f"检查表是否存在失败: {e}")
            return False
