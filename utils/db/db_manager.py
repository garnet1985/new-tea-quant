"""
简化的 MySQL 数据库管理器
- 使用 DBUtils 管理连接池（自动扩容、健康检查）
- 使用 SchemaManager 管理表结构
- 提供简洁的 CRUD 接口
"""
import pymysql
from typing import Optional, Dict, List, Any
from contextlib import contextmanager
from loguru import logger
from dbutils.pooled_db import PooledDB

from .db_config import DB_CONFIG
from .schema_manager import SchemaManager


class DatabaseManager:
    """
    简化的数据库管理器
    
    职责：
    - 连接池管理（使用 DBUtils）
    - 基础 CRUD 操作
    - 事务管理
    
    不再负责：
    - Schema 解析和建表（由 SchemaManager 负责）
    - 表模型缓存（归 DataLoader）
    - 异步操作
    - 写入队列
    """
    
    def __init__(self, config: Dict = None, is_verbose: bool = False):
        """
        初始化数据库管理器
        
        Args:
            config: 数据库配置（默认使用 DB_CONFIG）
            is_verbose: 是否输出详细日志
        """
        self.config = config or DB_CONFIG
        self.is_verbose = is_verbose
        self.pool = None
        self._initialized = False
        
        # Schema 管理器
        self.schema_manager = SchemaManager(
            charset=self.config['base']['charset'],
            is_verbose=is_verbose
        )
    
    def initialize(self):
        """
        初始化数据库管理器
        
        步骤：
        1. 创建数据库（如果不存在）
        2. 初始化连接池
        3. 加载并创建所有表
        """
        try:
            # 1. 确保数据库存在
            self._ensure_database_exists()
            
            # 2. 初始化连接池
            self._init_connection_pool()
            
            # 3. 创建基础表
            self.schema_manager.create_all_tables(self.get_connection)
            
            self._initialized = True
            
            if self.is_verbose:
                logger.info("✅ DatabaseManager 初始化完成")
                
        except Exception as e:
            logger.error(f"❌ DatabaseManager 初始化失败: {e}")
            raise
    
    def _ensure_database_exists(self):
        """确保数据库存在，不存在则创建"""
        try:
            # 先不指定数据库，连接到 MySQL
            temp_conn = pymysql.connect(
                host=self.config['base']['host'],
                user=self.config['base']['user'],
                password=self.config['base']['password'],
                port=self.config['base']['port'],
                charset=self.config['base']['charset']
            )
            
            try:
                with temp_conn.cursor() as cursor:
                    db_name = self.config['base']['database']
                    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET {self.config['base']['charset']}")
                    if self.is_verbose:
                        logger.info(f"✅ 数据库 {db_name} 已就绪")
            finally:
                temp_conn.close()
                
        except Exception as e:
            logger.error(f"❌ 创建数据库失败: {e}")
            raise
    
    def _init_connection_pool(self):
        """
        初始化连接池（使用 DBUtils）
        
        特性：
        - 自动扩容（从 min 到 max）
        - 自动健康检查（ping=1）
        - 线程安全
        - 连接复用
        """
        try:
            pool_config = self.config.get('pool', {})
            timeout_config = self.config.get('timeout', {})
            
            self.pool = PooledDB(
                creator=pymysql,
                
                # 连接池配置
                maxconnections=pool_config.get('pool_size_max', 30),  # 最大连接数
                mincached=pool_config.get('pool_size_min', 5),        # 最小空闲连接
                maxcached=10,                                          # 最大空闲连接
                maxshared=0,                                           # 最大共享连接（0=不共享）
                blocking=True,                                         # 连接用完时阻塞等待
                maxusage=None,                                         # 连接最大使用次数（None=无限制）
                
                # 健康检查
                ping=1,  # 0=不检查, 1=默认检查, 2=事务开始时检查, 4=执行查询时检查, 7=总是检查
                
                # 数据库连接参数
                host=self.config['base']['host'],
                user=self.config['base']['user'],
                password=self.config['base']['password'],
                database=self.config['base']['database'],
                port=self.config['base']['port'],
                charset=self.config['base']['charset'],
                
                # 超时配置
                connect_timeout=timeout_config.get('connection', 60),
                read_timeout=timeout_config.get('read', 60),
                write_timeout=timeout_config.get('write', 60),
                
                # 其他配置
                autocommit=self.config['base'].get('autocommit', True),
                cursorclass=pymysql.cursors.DictCursor,  # 返回字典格式
            )
            
            if self.is_verbose:
                logger.info(f"✅ 连接池初始化完成（最小: {pool_config.get('pool_size_min', 5)}, 最大: {pool_config.get('pool_size_max', 30)}）")
                
        except Exception as e:
            logger.error(f"❌ 连接池初始化失败: {e}")
            raise
    
    # ==================== 连接管理 ====================
    
    @contextmanager
    def get_connection(self):
        """
        获取数据库连接（上下文管理器）
        
        使用方式:
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(...)
        """
        if not self.pool:
            raise RuntimeError("连接池未初始化，请先调用 initialize()")
        
        conn = self.pool.connection()
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()  # DBUtils 会自动归还到池中
    
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
        with self.get_connection() as conn:
            # 临时关闭自动提交
            old_autocommit = conn.get_autocommit()
            conn.autocommit(False)
            
            cursor = conn.cursor()
            try:
                yield cursor
                conn.commit()
            except Exception as e:
                conn.rollback()
                raise
            finally:
                cursor.close()
                conn.autocommit(old_autocommit)
    
    # ==================== 基础 CRUD ====================
    
    def execute(self, sql: str, params: Any = None) -> int:
        """
        执行 SQL（INSERT/UPDATE/DELETE）
        
        Args:
            sql: SQL 语句
            params: 参数
            
        Returns:
            影响的行数
        """
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                affected = cursor.execute(sql, params)
                return affected
    
    def fetch_one(self, sql: str, params: Any = None) -> Optional[Dict]:
        """
        查询单条记录
        
        Args:
            sql: SQL 语句
            params: 参数
            
        Returns:
            字典格式的记录，不存在返回 None
        """
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchone()
    
    def fetch_all(self, sql: str, params: Any = None) -> List[Dict]:
        """
        查询多条记录
        
        Args:
            sql: SQL 语句
            params: 参数
            
        Returns:
            字典列表
        """
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchall()
    
    def insert(self, table: str, data: Dict) -> int:
        """
        插入单条记录
        
        Args:
            table: 表名
            data: 数据字典
            
        Returns:
            插入的记录 ID
        """
        fields = ', '.join([f"`{k}`" for k in data.keys()])
        placeholders = ', '.join(['%s'] * len(data))
        sql = f"INSERT INTO `{table}` ({fields}) VALUES ({placeholders})"
        
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, list(data.values()))
                return cursor.lastrowid
    
    def bulk_insert(self, table: str, data_list: List[Dict], ignore_duplicates: bool = False) -> int:
        """
        批量插入记录
        
        Args:
            table: 表名
            data_list: 数据字典列表
            ignore_duplicates: 是否忽略重复记录
            
        Returns:
            插入的记录数
        """
        if not data_list:
            return 0
        
        # 使用第一条记录的键作为字段
        fields = list(data_list[0].keys())
        fields_str = ', '.join([f"`{k}`" for k in fields])
        placeholders = ', '.join(['%s'] * len(fields))
        
        ignore_keyword = 'IGNORE' if ignore_duplicates else ''
        sql = f"INSERT {ignore_keyword} INTO `{table}` ({fields_str}) VALUES ({placeholders})"
        
        # 准备数据
        values = [tuple(row.get(k) for k in fields) for row in data_list]
        
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                affected = cursor.executemany(sql, values)
                return affected
    
    def update(self, table: str, data: Dict, where: str, params: Any = None) -> int:
        """
        更新记录
        
        Args:
            table: 表名
            data: 要更新的数据字典
            where: WHERE 条件（不包含 WHERE 关键字）
            params: WHERE 条件的参数
            
        Returns:
            影响的行数
            
        Example:
            db.update('stock_kline', {'close': 100}, 'id = %s AND date = %s', ['000001.SZ', '20240101'])
        """
        set_clause = ', '.join([f"`{k}` = %s" for k in data.keys()])
        sql = f"UPDATE `{table}` SET {set_clause} WHERE {where}"
        
        # 合并参数
        all_params = list(data.values())
        if params:
            if isinstance(params, (list, tuple)):
                all_params.extend(params)
            else:
                all_params.append(params)
        
        return self.execute(sql, all_params)
    
    def delete(self, table: str, where: str, params: Any = None) -> int:
        """
        删除记录
        
        Args:
            table: 表名
            where: WHERE 条件（不包含 WHERE 关键字）
            params: WHERE 条件的参数
            
        Returns:
            影响的行数
        """
        sql = f"DELETE FROM `{table}` WHERE {where}"
        return self.execute(sql, params)
    
    def select(self, table: str, fields: str = '*', where: str = None, 
               params: Any = None, order_by: str = None, limit: int = None) -> List[Dict]:
        """
        查询记录（便捷方法）
        
        Args:
            table: 表名
            fields: 字段（默认 *）
            where: WHERE 条件
            params: WHERE 参数
            order_by: 排序
            limit: 限制数量
            
        Returns:
            记录列表
        """
        sql = f"SELECT {fields} FROM `{table}`"
        
        if where:
            sql += f" WHERE {where}"
        
        if order_by:
            sql += f" ORDER BY {order_by}"
        
        if limit:
            sql += f" LIMIT {limit}"
        
        return self.fetch_all(sql, params)
    
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
        return self.schema_manager.is_table_exists(
            table_name, 
            self.config['base']['database'], 
            self.get_connection()
        )
    
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
        """关闭连接池"""
        if self.pool:
            self.pool.close()
            self.pool = None
            if self.is_verbose:
                logger.info("✅ 连接池已关闭")
    
    def get_stats(self) -> Dict:
        """
        获取连接池统计信息
        
        Returns:
            统计信息字典
        """
        if not self.pool:
            return {}
        
        pool_config = self.config.get('pool', {})
        return {
            'initialized': self._initialized,
            'max_connections': pool_config.get('pool_size_max', 30),
            'min_cached': pool_config.get('pool_size_min', 5),
        }
    
    def __del__(self):
        """析构函数：确保连接池关闭"""
        try:
            self.close()
        except:
            pass
