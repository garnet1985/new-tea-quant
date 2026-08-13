"""
PgsqlConnector — PostgreSQL 连接池、事务、SQL 执行。

方言 SQL 文本见 ``pgsql.sql_adapter.PgsqlSqlAdapter``。
"""
from __future__ import annotations

from core.infra.cmd_layout import i

import logging
from contextlib import contextmanager
from typing import Any, Dict, Iterator, List, Optional

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor, execute_batch

from core.infra.db.core.engines.shared.query_rows import normalize_query_rows
from core.infra.db.core.engines.pgsql.settings import PgsqlSettings
from core.infra.db.core.engines.pgsql.sql_adapter import PgsqlSqlAdapter

logger = logging.getLogger(__name__)


class PgsqlConnector:
    """PostgreSQL 连接与执行（engine 包内专用）。"""

    def __init__(
        self,
        settings: PgsqlSettings | Dict[str, Any],
        *,
        is_verbose: bool = False,
    ) -> None:
        if isinstance(settings, dict):
            settings = PgsqlSettings.from_dict(settings)
        self.settings = settings
        self.config = settings.as_dict()
        self.is_verbose = is_verbose
        self.sql_adapter = PgsqlSqlAdapter()
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
                logger.info(f"{i('success')} PostgreSQL 连接池创建成功: {self.config['database']} (pool_size={maxconn})")
            
            return self._connection_pool
            
        except Exception as e:
            logger.error(f"{i('error')} PostgreSQL 连接失败: {e}")
            raise
    
    def close(self):
        """关闭连接池"""
        if self._connection_pool:
            self._connection_pool.closeall()
            self._connection_pool = None
            self._initialized = False
            if self.is_verbose:
                logger.info(f"{i('success')} PostgreSQL 连接池已关闭")
    
    def _get_connection(self):
        """从连接池获取连接"""
        if not self._connection_pool or not self._initialized:
            # 尝试自动连接（如果配置存在）
            if self.config:
                logger.warning("PgsqlConnector 连接池未初始化，尝试自动连接...")
                self.connect()
            else:
                raise RuntimeError("PgsqlConnector 未初始化，请先调用 connect()")
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
        # 检查适配器是否已初始化
        if not self._initialized or not self._connection_pool:
            if self.config:
                logger.warning("PgsqlConnector 未初始化，尝试自动连接...")
                self.connect()
            else:
                raise RuntimeError("PgsqlConnector 未初始化，请先调用 connect()")
        
        conn = None
        try:
            # 标准化查询语句（转换占位符）
            query = self.sql_adapter.normalize_query(query)
            
            conn = self._get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                results = cursor.fetchall()
                # RealDictRow → dict；读出口统一 DECIMAL→float 等标量规范
                return normalize_query_rows([dict(row) for row in results])
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
        # 检查适配器是否已初始化
        if not self._initialized or not self._connection_pool:
            if self.config:
                logger.warning("PgsqlConnector 未初始化，尝试自动连接...")
                self.connect()
            else:
                raise RuntimeError("PgsqlConnector 未初始化，请先调用 connect()")
        
        conn = None
        try:
            # 标准化查询语句（转换占位符）
            query = self.sql_adapter.normalize_query(query)
            
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
        # 检查适配器是否已初始化
        if not self._initialized or not self._connection_pool:
            # 尝试自动连接（如果配置存在）
            if self.config:
                self.connect()
            else:
                raise RuntimeError("PgsqlConnector 未初始化，请先调用 connect()")
        
        conn = None
        try:
            # 标准化查询语句（转换占位符）
            query = self.sql_adapter.normalize_query(query)
            
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
    
    @contextmanager
    def connection(self) -> Iterator[Any]:
        conn = self.get_connection()
        try:
            yield conn
        finally:
            self._put_connection(conn.pg_conn)

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
            def __init__(self, pg_conn, connector: "PgsqlConnector"):
                self.pg_conn = pg_conn
                self.connector = connector
                self.adapter = connector
            
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
        query, params = self.sql_adapter.table_exists_query_and_params(
            self.config, table_name
        )
        try:
            rows = self.execute_query(query, params)
            return self.sql_adapter.parse_exists_count(rows[0] if rows else {})
        except Exception as e:
            logger.error("检查表是否存在失败: %s", e)
            return False


