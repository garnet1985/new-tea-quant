"""
MySQLAdapter - MySQL 数据库适配器

实现 MySQL 数据库的连接和操作。
"""
import pymysql
from pymysql.cursors import DictCursor
from typing import Dict, List, Any, Optional
from contextlib import contextmanager
import logging
import threading
from queue import LifoQueue, Empty as QueueEmpty

from .base_adapter import BaseDatabaseAdapter


logger = logging.getLogger(__name__)


class MySQLAdapter(BaseDatabaseAdapter):
    """
    MySQL 数据库适配器
    
    特性：
    - 使用 pymysql 连接
    - 支持连接池（可选）
    - 返回字典格式的结果
    """
    
    def __init__(self, config: Dict[str, Any], is_verbose: bool = False):
        """
        初始化 MySQL 适配器
        
        Args:
            config: MySQL 配置字典
                - host: 主机地址
                - port: 端口（默认 3306）
                - database: 数据库名
                - user: 用户名
                - password: 密码
                - charset: 字符集（默认 utf8mb4）
                - autocommit: 自动提交（默认 True）
            is_verbose: 是否输出详细日志
        """
        self.config = config
        self.is_verbose = is_verbose
        self.conn: Optional[pymysql.Connection] = None  # 兼容旧代码
        self._pool: Optional[LifoQueue] = None
        self._pool_lock = threading.Lock()
        self._all_connections = set()
        self._pool_maxconn = 10
        self._initialized = False

    def _create_connection(self) -> pymysql.Connection:
        conn_params = {
            'host': self.config['host'],
            'port': self.config.get('port', 3306),
            'database': self.config['database'],
            'user': self.config['user'],
            'password': self.config['password'],
            'charset': self.config.get('charset', 'utf8mb4'),
            'autocommit': self.config.get('autocommit', True),
            'cursorclass': DictCursor,
        }
        return pymysql.connect(**conn_params)

    def _is_connection_alive(self, conn: Optional[pymysql.Connection]) -> bool:
        if hasattr(conn, "mysql_conn"):
            conn = conn.mysql_conn
        if not conn:
            return False
        try:
            conn.ping(reconnect=True)
            return True
        except Exception:
            return False

    def _discard_connection(self, conn: Optional[pymysql.Connection]) -> None:
        if hasattr(conn, "mysql_conn"):
            conn = conn.mysql_conn
        if not conn:
            return
        try:
            conn.close()
        except Exception:
            pass
        with self._pool_lock:
            self._all_connections.discard(conn)

    def _get_connection(self) -> pymysql.Connection:
        if not self._initialized or self._pool is None:
            if self.config:
                self.connect()
            else:
                raise RuntimeError("MySQL 适配器未初始化，请先调用 connect()")
        conn = None
        try:
            conn = self._pool.get_nowait()
        except QueueEmpty:
            with self._pool_lock:
                if len(self._all_connections) < self._pool_maxconn:
                    conn = self._create_connection()
                    self._all_connections.add(conn)
        if conn is None:
            conn = self._pool.get(timeout=5)
        if not self._is_connection_alive(conn):
            self._discard_connection(conn)
            with self._pool_lock:
                conn = self._create_connection()
                self._all_connections.add(conn)
        return conn

    def _put_connection(self, conn: Optional[pymysql.Connection]) -> None:
        if hasattr(conn, "mysql_conn"):
            conn = conn.mysql_conn
        if not conn:
            return
        if self._pool is None:
            self._discard_connection(conn)
            return
        if not self._is_connection_alive(conn):
            self._discard_connection(conn)
            return
        try:
            self._pool.put_nowait(conn)
        except Exception:
            self._discard_connection(conn)
    
    def connect(self, config: Dict[str, Any] = None) -> pymysql.Connection:
        """
        建立 MySQL 连接
        
        Args:
            config: 数据库配置（如果提供，会覆盖初始化时的配置）
            
        Returns:
            MySQL 连接对象
        """
        if config:
            self.config = config
        
        try:
            maxconn = int(self.config.get('pool_maxconn', self.config.get('pool_size', 10)))
            minconn = int(self.config.get('pool_minconn', 1))
            if maxconn < 1:
                maxconn = 1
            if minconn < 1:
                minconn = 1
            if minconn > maxconn:
                minconn = maxconn
            self._pool_maxconn = maxconn
            self._pool = LifoQueue(maxsize=maxconn)
            self._all_connections = set()
            for _ in range(minconn):
                conn = self._create_connection()
                self._all_connections.add(conn)
                self._pool.put(conn)
            # 兼容旧代码路径：保留一个主连接引用
            self.conn = next(iter(self._all_connections), None)
            self._initialized = True
            
            if self.is_verbose:
                logger.info(
                    f"✅ MySQL 连接池创建成功: {self.config['host']}:{self.config.get('port', 3306)}/{self.config['database']} "
                    f"(pool_size={self._pool_maxconn})"
                )
            
            return self.conn
            
        except Exception as e:
            logger.error(f"❌ MySQL 连接失败: {e}")
            raise
    
    def close(self):
        """关闭连接"""
        for conn in list(self._all_connections):
            try:
                conn.close()
            except Exception:
                pass
        self._all_connections = set()
        self._pool = None
        self.conn = None
        self._initialized = False
        if self.is_verbose:
            logger.info("✅ MySQL 连接池已关闭")
    
    def execute_query(self, query: str, params: Any = None) -> List[Dict[str, Any]]:
        """
        执行查询语句
        
        Args:
            query: SQL 查询语句（使用 %s 占位符，或 ? 会自动转换）
            params: 查询参数
            
        Returns:
            查询结果列表（字典格式）
        """
        if not self._initialized or self._pool is None:
            if self.config:
                self.connect()
            else:
                raise RuntimeError("MySQL 适配器未初始化，请先调用 connect()")
        
        conn = None
        try:
            # 标准化查询语句（转换占位符）
            query = self.normalize_query(query)
            conn = self._get_connection()
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                results = cursor.fetchall()
                # DictCursor 返回的是字典列表
                return list(results) if results else []
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
        if not self._initialized or self._pool is None:
            if self.config:
                self.connect()
            else:
                raise RuntimeError("MySQL 适配器未初始化，请先调用 connect()")
        
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
        if not self._initialized or self._pool is None:
            if self.config:
                self.connect()
            else:
                raise RuntimeError("MySQL 适配器未初始化，请先调用 connect()")
        
        conn = None
        try:
            # 标准化查询语句（转换占位符）
            query = self.normalize_query(query)
            conn = self._get_connection()
            with conn.cursor() as cursor:
                cursor.executemany(query, params_list)
                conn.commit()
                return cursor.rowcount
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
        if not self._initialized or self._pool is None:
            if self.config:
                self.connect()
            else:
                raise RuntimeError("MySQL 适配器未初始化，请先调用 connect()")
        
        # 临时关闭自动提交
        conn = self._get_connection()
        old_autocommit = conn.get_autocommit()
        conn.autocommit(False)
        
        try:
            with conn.cursor() as cursor:
                yield cursor
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.autocommit(old_autocommit)
            self._put_connection(conn)
    
    def get_placeholder(self) -> str:
        """返回 MySQL 占位符类型"""
        return '%s'
    
    def get_connection(self):
        """
        获取数据库连接（用于需要直接访问连接的场景）

        返回包装对象，与 PostgreSQL 适配器一致，提供 ``conn.execute(sql)``，
        供 SchemaManager 等使用（原始 pymysql.Connection 无 ``execute``，须通过游标执行）。

        Returns:
            带 execute/cursor/commit/rollback 的包装对象
        """
        if not self._initialized or self._pool is None:
            if self.config:
                self.connect()
            else:
                raise RuntimeError("MySQL 适配器未初始化，请先调用 connect()")

        mysql_conn = self._get_connection()

        class MySQLConnectionWrapper:
            def __init__(self, raw, adapter):
                self.mysql_conn = raw
                self.adapter = adapter

            def execute(self, query: str, params: Any = None):
                with self.mysql_conn.cursor() as cursor:
                    if params is None:
                        cursor.execute(query)
                    else:
                        cursor.execute(query, params)
                self.mysql_conn.commit()
                return self

            def cursor(self):
                return self.mysql_conn.cursor()

            def commit(self):
                self.mysql_conn.commit()

            def rollback(self):
                self.mysql_conn.rollback()

        return MySQLConnectionWrapper(mysql_conn, self)
    
    def is_table_exists(self, table_name: str) -> bool:
        """
        检查表是否存在
        
        Args:
            table_name: 表名
            
        Returns:
            是否存在
        """
        query = """
            SELECT COUNT(*) as count 
            FROM information_schema.tables 
            WHERE table_schema = DATABASE() AND table_name = %s
        """
        try:
            result = self.execute_query(query, (table_name,))
            return result[0]['count'] > 0 if result else False
        except Exception as e:
            logger.error(f"检查表是否存在失败: {e}")
            return False
