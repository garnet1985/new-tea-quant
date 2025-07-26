"""
MySQL Database Connection Manager
"""
import pymysql
import asyncio
from typing import Optional, Dict, List, Any
from contextlib import asynccontextmanager
from loguru import logger
from .config import DB_CONFIG, POOL_CONFIG


class DatabaseConnection:
    """MySQL数据库连接管理器"""
    
    def __init__(self):
        self.pool = None
        self.is_initialized = False
        
    async def initialize(self):
        """初始化数据库连接池"""
        try:
            # 创建连接池
            self.pool = await self._create_connection_pool()
            self.is_initialized = True
            logger.info("Database connection pool initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database connection pool: {e}")
            raise
    
    async def _create_connection_pool(self):
        """创建连接池"""
        return await pymysql.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database=DB_CONFIG['database'],
            port=DB_CONFIG['port'],
            charset=DB_CONFIG['charset'],
            autocommit=DB_CONFIG['autocommit'],
            max_allowed_packet=16777216,  # 16MB
            connect_timeout=60,
            read_timeout=60,
            write_timeout=60,
        )
    
    @asynccontextmanager
    async def get_connection(self):
        """获取数据库连接的上下文管理器"""
        if not self.is_initialized:
            await self.initialize()
        
        connection = None
        try:
            connection = await self.pool.connect()
            yield connection
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            if connection:
                await connection.rollback()
            raise
        finally:
            if connection:
                await connection.close()
    
    async def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """执行查询语句"""
        async with self.get_connection() as conn:
            async with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                await cursor.execute(query, params)
                result = await cursor.fetchall()
                return result
    
    async def execute_many(self, query: str, params: List[tuple]) -> int:
        """批量执行SQL语句"""
        async with self.get_connection() as conn:
            async with conn.cursor() as cursor:
                affected_rows = await cursor.executemany(query, params)
                await conn.commit()
                return affected_rows
    
    async def execute_update(self, query: str, params: Optional[tuple] = None) -> int:
        """执行更新语句"""
        async with self.get_connection() as conn:
            async with conn.cursor() as cursor:
                affected_rows = await cursor.execute(query, params)
                await conn.commit()
                return affected_rows
    
    async def insert_data(self, table: str, data: Dict[str, Any]) -> int:
        """插入数据"""
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        
        return await self.execute_update(query, tuple(data.values()))
    
    async def insert_many(self, table: str, data_list: List[Dict[str, Any]]) -> int:
        """批量插入数据"""
        if not data_list:
            return 0
            
        columns = list(data_list[0].keys())
        placeholders = ', '.join(['%s'] * len(columns))
        query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
        
        values = [tuple(data[col] for col in columns) for data in data_list]
        return await self.execute_many(query, values)
    
    async def update_data(self, table: str, data: Dict[str, Any], condition: str, params: tuple) -> int:
        """更新数据"""
        set_clause = ', '.join([f"{k} = %s" for k in data.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE {condition}"
        
        all_params = tuple(data.values()) + params
        return await self.execute_update(query, all_params)
    
    async def delete_data(self, table: str, condition: str, params: tuple) -> int:
        """删除数据"""
        query = f"DELETE FROM {table} WHERE {condition}"
        return await self.execute_update(query, params)
    
    async def table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        query = """
        SELECT COUNT(*) as count 
        FROM information_schema.tables 
        WHERE table_schema = %s AND table_name = %s
        """
        result = await self.execute_query(query, (DB_CONFIG['database'], table_name))
        return result[0]['count'] > 0
    
    async def get_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """获取表结构信息"""
        query = f"DESCRIBE {table_name}"
        return await self.execute_query(query)
    
    async def close(self):
        """关闭数据库连接"""
        if self.pool:
            await self.pool.close()
            self.is_initialized = False
            logger.info("Database connection pool closed")


# 全局数据库连接实例
db_connection = DatabaseConnection()


async def get_db_connection() -> DatabaseConnection:
    """获取数据库连接实例"""
    if not db_connection.is_initialized:
        await db_connection.initialize()
    return db_connection 