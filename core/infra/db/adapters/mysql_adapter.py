"""
MySQLAdapter - MySQL 数据库适配器

实现 MySQL 数据库的连接和操作。
"""
import pymysql
from pymysql.cursors import DictCursor
from typing import Dict, List, Any, Optional
from contextlib import contextmanager
from loguru import logger

from .base_adapter import BaseDatabaseAdapter


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
        self.conn: Optional[pymysql.Connection] = None
        self._initialized = False
    
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
            # MySQL 连接参数
            conn_params = {
                'host': self.config['host'],
                'port': self.config.get('port', 3306),
                'database': self.config['database'],
                'user': self.config['user'],
                'password': self.config['password'],
                'charset': self.config.get('charset', 'utf8mb4'),
                'autocommit': self.config.get('autocommit', True),
                'cursorclass': DictCursor,  # 使用字典游标
            }
            
            self.conn = pymysql.connect(**conn_params)
            self._initialized = True
            
            if self.is_verbose:
                logger.info(f"✅ MySQL 连接成功: {self.config['host']}:{self.config.get('port', 3306)}/{self.config['database']}")
            
            return self.conn
            
        except Exception as e:
            logger.error(f"❌ MySQL 连接失败: {e}")
            raise
    
    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()
            self.conn = None
            self._initialized = False
            if self.is_verbose:
                logger.info("✅ MySQL 连接已关闭")
    
    def execute_query(self, query: str, params: Any = None) -> List[Dict[str, Any]]:
        """
        执行查询语句
        
        Args:
            query: SQL 查询语句（使用 %s 占位符）
            params: 查询参数
            
        Returns:
            查询结果列表（字典格式）
        """
        if not self.conn:
            raise RuntimeError("MySQL 适配器未初始化，请先调用 connect()")
        
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(query, params)
                results = cursor.fetchall()
                # DictCursor 返回的是字典列表
                return list(results) if results else []
        except Exception as e:
            logger.error(f"执行查询失败: {e}\n查询: {query}\n参数: {params}")
            raise
    
    def execute_write(self, query: str, params: Any = None) -> int:
        """
        执行写入语句
        
        Args:
            query: SQL 写入语句
            params: 查询参数
            
        Returns:
            影响的行数
        """
        if not self.conn:
            raise RuntimeError("MySQL 适配器未初始化，请先调用 connect()")
        
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(query, params)
                self.conn.commit()
                return cursor.rowcount
        except Exception as e:
            if self.conn:
                self.conn.rollback()
            logger.error(f"执行写入失败: {e}\n查询: {query}\n参数: {params}")
            raise
    
    def execute_batch(self, query: str, params_list: List[Any]) -> int:
        """
        批量执行写入语句
        
        Args:
            query: SQL 写入语句
            params_list: 参数列表
            
        Returns:
            总影响的行数
        """
        if not self.conn:
            raise RuntimeError("MySQL 适配器未初始化，请先调用 connect()")
        
        try:
            with self.conn.cursor() as cursor:
                cursor.executemany(query, params_list)
                self.conn.commit()
                return cursor.rowcount
        except Exception as e:
            if self.conn:
                self.conn.rollback()
            logger.error(f"批量写入失败: {e}\n查询: {query}\n记录数: {len(params_list)}")
            raise
    
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
        if not self.conn:
            raise RuntimeError("MySQL 适配器未初始化，请先调用 connect()")
        
        # 临时关闭自动提交
        old_autocommit = self.conn.autocommit
        self.conn.autocommit = False
        
        try:
            with self.conn.cursor() as cursor:
                yield cursor
                self.conn.commit()
        except Exception as e:
            if self.conn:
                self.conn.rollback()
            raise
        finally:
            self.conn.autocommit = old_autocommit
    
    def get_placeholder(self) -> str:
        """返回 MySQL 占位符类型"""
        return '%s'
    
    def get_connection(self):
        """
        获取数据库连接（用于需要直接访问连接的场景）
        
        Returns:
            MySQL 连接对象
        """
        if not self.conn:
            raise RuntimeError("MySQL 适配器未初始化，请先调用 connect()")
        return self.conn
    
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
