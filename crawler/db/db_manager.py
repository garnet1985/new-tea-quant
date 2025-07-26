"""
Unified MySQL Database Manager
支持同步和异步操作
"""
import pymysql
import asyncio
from typing import Optional, Dict, List, Any
from contextlib import contextmanager
from loguru import logger
from .config import DB_CONFIG


class DatabaseManager:
    """统一的MySQL数据库管理器 - 支持同步和异步操作"""
    
    def __init__(self):
        # 同步连接
        self.sync_connection = None
        self.is_sync_connected = False
        
        # 异步连接
        self.async_pool = None
        self.is_async_initialized = False
        
    # ==================== 同步连接方法 ====================
    
    def connect_sync(self):
        """建立同步数据库连接"""
        try:
            self.sync_connection = pymysql.connect(
                host=DB_CONFIG['base']['host'],
                user=DB_CONFIG['base']['user'],
                password=DB_CONFIG['base']['password'],
                database=DB_CONFIG['base']['database'],
                port=DB_CONFIG['base']['port'],
                charset=DB_CONFIG['base']['charset'],
                autocommit=DB_CONFIG['base']['autocommit'],
                max_allowed_packet=DB_CONFIG['performance']['max_allowed_packet'],
                connect_timeout=DB_CONFIG['timeout']['connection'],
                read_timeout=DB_CONFIG['timeout']['read'],
                write_timeout=DB_CONFIG['timeout']['write'],
            )
            self.is_sync_connected = True
            logger.info("Synchronous database connected successfully")
        except Exception as e:
            logger.error(f"Failed to connect to database synchronously: {e}")
            raise
    
    def disconnect_sync(self):
        """断开同步数据库连接"""
        if self.sync_connection:
            self.sync_connection.close()
            self.is_sync_connected = False
            logger.info("Synchronous database disconnected")
    
    @contextmanager
    def get_sync_cursor(self):
        """获取同步数据库游标的上下文管理器"""
        if not self.is_sync_connected:
            self.connect_sync()
        
        cursor = None
        try:
            cursor = self.sync_connection.cursor(pymysql.cursors.DictCursor)
            yield cursor
        except Exception as e:
            logger.error(f"Synchronous database cursor error: {e}")
            if self.sync_connection:
                self.sync_connection.rollback()
            raise
        finally:
            if cursor:
                cursor.close()
    
    def execute_sync_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """执行同步查询语句"""
        with self.get_sync_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()
    
    def execute_sync_many(self, query: str, params: List[tuple]) -> int:
        """批量执行同步SQL语句"""
        with self.get_sync_cursor() as cursor:
            affected_rows = cursor.executemany(query, params)
            self.sync_connection.commit()
            return affected_rows
    
    def execute_sync_update(self, query: str, params: Optional[tuple] = None) -> int:
        """执行同步更新语句"""
        with self.get_sync_cursor() as cursor:
            affected_rows = cursor.execute(query, params)
            self.sync_connection.commit()
            return affected_rows
    
    def insert_sync_data(self, table: str, data: Dict[str, Any]) -> int:
        """同步插入数据"""
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        
        return self.execute_sync_update(query, tuple(data.values()))
    
    def insert_sync_many(self, table: str, data_list: List[Dict[str, Any]]) -> int:
        """同步批量插入数据"""
        if not data_list:
            return 0
            
        columns = list(data_list[0].keys())
        placeholders = ', '.join(['%s'] * len(columns))
        query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
        
        values = [tuple(data[col] for col in columns) for data in data_list]
        return self.execute_sync_many(query, values)
    
    # ==================== 异步连接方法 ====================
    
    async def initialize_async(self):
        """初始化异步数据库连接池"""
        try:
            # 创建异步连接池
            self.async_pool = await self._create_async_connection_pool()
            self.is_async_initialized = True
            logger.info("Asynchronous database connection pool initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize asynchronous database connection pool: {e}")
            raise
    
    async def _create_async_connection_pool(self):
        """创建异步连接池"""
        return await pymysql.connect(
            host=DB_CONFIG['base']['host'],
            user=DB_CONFIG['base']['user'],
            password=DB_CONFIG['base']['password'],
            database=DB_CONFIG['base']['database'],
            port=DB_CONFIG['base']['port'],
            charset=DB_CONFIG['base']['charset'],
            autocommit=DB_CONFIG['base']['autocommit'],
            max_allowed_packet=16777216,  # 16MB
            connect_timeout=DB_CONFIG['pool']['connection_timeout'],
            read_timeout=DB_CONFIG['pool']['read_timeout'],
            write_timeout=DB_CONFIG['pool']['write_timeout'],
        )
    
    async def get_async_connection(self):
        """获取异步数据库连接"""
        if not self.is_async_initialized:
            await self.initialize_async()
        return self.async_pool
    
    async def execute_async_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """执行异步查询语句"""
        connection = await self.get_async_connection()
        async with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            await cursor.execute(query, params)
            result = await cursor.fetchall()
            return result
    
    async def execute_async_update(self, query: str, params: Optional[tuple] = None) -> int:
        """执行异步更新语句"""
        connection = await self.get_async_connection()
        async with connection.cursor() as cursor:
            affected_rows = await cursor.execute(query, params)
            await connection.commit()
            return affected_rows
    
    async def insert_async_data(self, table: str, data: Dict[str, Any]) -> int:
        """异步插入数据"""
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        
        return await self.execute_async_update(query, tuple(data.values()))
    
    # ==================== 通用工具方法 ====================
    
    def table_exists_sync(self, table_name: str) -> bool:
        """同步检查表是否存在"""
        query = """
        SELECT COUNT(*) as count 
        FROM information_schema.tables 
        WHERE table_schema = %s AND table_name = %s
        """
        result = self.execute_sync_query(query, (DB_CONFIG['base']['database'], table_name))
        return result[0]['count'] > 0
    
    async def table_exists_async(self, table_name: str) -> bool:
        """异步检查表是否存在"""
        query = """
        SELECT COUNT(*) as count 
        FROM information_schema.tables 
        WHERE table_schema = %s AND table_name = %s
        """
        result = await self.execute_async_query(query, (DB_CONFIG['base']['database'], table_name))
        return result[0]['count'] > 0
    
    def get_table_info_sync(self, table_name: str) -> List[Dict[str, Any]]:
        """同步获取表结构信息"""
        query = f"DESCRIBE {table_name}"
        return self.execute_sync_query(query)
    
    async def get_table_info_async(self, table_name: str) -> List[Dict[str, Any]]:
        """异步获取表结构信息"""
        query = f"DESCRIBE {table_name}"
        return await self.execute_async_query(query)
    
    def get_table_count_sync(self, table_name: str, condition: str = "1=1", params: tuple = ()) -> int:
        """同步获取表记录数"""
        query = f"SELECT COUNT(*) as count FROM {table_name} WHERE {condition}"
        result = self.execute_sync_query(query, params)
        return result[0]['count'] if result else 0
    
    async def get_table_count_async(self, table_name: str, condition: str = "1=1", params: tuple = ()) -> int:
        """异步获取表记录数"""
        query = f"SELECT COUNT(*) as count FROM {table_name} WHERE {condition}"
        result = await self.execute_async_query(query, params)
        return result[0]['count'] if result else 0
    
    def execute_sync_transaction(self, queries: List[tuple]) -> bool:
        """执行同步事务"""
        try:
            with self.get_sync_cursor() as cursor:
                for query, params in queries:
                    cursor.execute(query, params)
                self.sync_connection.commit()
                return True
        except Exception as e:
            logger.error(f"Synchronous transaction failed: {e}")
            self.sync_connection.rollback()
            return False
    
    async def execute_async_transaction(self, queries: List[tuple]) -> bool:
        """执行异步事务"""
        try:
            connection = await self.get_async_connection()
            async with connection.cursor() as cursor:
                for query, params in queries:
                    await cursor.execute(query, params)
                await connection.commit()
                return True
        except Exception as e:
            logger.error(f"Asynchronous transaction failed: {e}")
            await connection.rollback()
            return False
    
    # ==================== 兼容性方法 ====================
    
    # 为了保持向后兼容，提供一些别名方法
    def connect(self):
        """兼容性方法：建立同步连接"""
        return self.connect_sync()
    
    def disconnect(self):
        """兼容性方法：断开同步连接"""
        return self.disconnect_sync()
    
    @contextmanager
    def get_cursor(self):
        """兼容性方法：获取同步游标"""
        return self.get_sync_cursor()
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """兼容性方法：执行同步查询"""
        return self.execute_sync_query(query, params)
    
    def execute_many(self, query: str, params: List[tuple]) -> int:
        """兼容性方法：批量执行同步SQL"""
        return self.execute_sync_many(query, params)
    
    def execute_update(self, query: str, params: Optional[tuple] = None) -> int:
        """兼容性方法：执行同步更新"""
        return self.execute_sync_update(query, params)
    
    def insert_data(self, table: str, data: Dict[str, Any]) -> int:
        """兼容性方法：同步插入数据"""
        return self.insert_sync_data(table, data)
    
    def insert_many(self, table: str, data_list: List[Dict[str, Any]]) -> int:
        """兼容性方法：同步批量插入数据"""
        return self.insert_sync_many(table, data_list)
    
    # ==================== 数据库管理方法 ====================
    
    def create_db(self):
        """创建数据库（如果不存在）"""
        try:
            # 连接到MySQL服务器（不指定数据库）
            temp_connection = pymysql.connect(
                host=DB_CONFIG['base']['host'],
                user=DB_CONFIG['base']['user'],
                password=DB_CONFIG['base']['password'],
                port=DB_CONFIG['base']['port'],
                charset=DB_CONFIG['base']['charset'],
            )
            
            with temp_connection.cursor() as cursor:
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_CONFIG['base']['database']}` CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci")
                logger.info(f"Database '{DB_CONFIG['base']['database']}' created or already exists")
            
            temp_connection.close()
            return True
            
        except Exception as e:
            logger.error(f"Failed to create database: {e}")
            return False
    
    def create_tables(self):
        """创建基础表（如果不存在）"""
        try:
            if not self.is_sync_connected:
                self.connect_sync()
            
            # 创建股票指数表
            create_stock_index_sql = """
            CREATE TABLE IF NOT EXISTS stock_index (
                code INT(10) PRIMARY KEY,
                name TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
                market TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
                industry TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
                isAlive TINYINT(1),
                type TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
                lastUpdate DATE NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
            """
            
            with self.get_sync_cursor() as cursor:
                cursor.execute(create_stock_index_sql)
                logger.info("Table 'stock_index' created or already exists")
            
            # 可以在这里添加更多表的创建语句
            # 例如：stock_kline, stock_detail, industry_index 等
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            return False
    
    def create_indexes(self):
        """创建索引（如果不存在）"""
        try:
            if not self.is_sync_connected:
                self.connect_sync()
            
            # 为stock_index表创建索引
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_stock_index_market ON stock_index(market)",
                "CREATE INDEX IF NOT EXISTS idx_stock_index_industry ON stock_index(industry)",
                "CREATE INDEX IF NOT EXISTS idx_stock_index_type ON stock_index(type)",
            ]
            
            with self.get_sync_cursor() as cursor:
                for index_sql in indexes:
                    try:
                        cursor.execute(index_sql)
                        logger.info(f"Index created: {index_sql}")
                    except Exception as e:
                        logger.warning(f"Failed to create index: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")
            return False


# 全局数据库管理器实例
db_manager = DatabaseManager()


def get_db_manager() -> DatabaseManager:
    """获取数据库管理器实例"""
    return db_manager


def get_sync_db_manager() -> DatabaseManager:
    """获取同步数据库管理器实例（兼容性函数）"""
    if not db_manager.is_sync_connected:
        db_manager.connect_sync()
    return db_manager 