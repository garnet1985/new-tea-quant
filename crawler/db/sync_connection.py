"""
Synchronous MySQL Database Connection Manager
"""
import pymysql
from typing import Optional, Dict, List, Any
from contextlib import contextmanager
from loguru import logger
from .config import DB_CONFIG


class SyncDatabaseConnection:
    """同步MySQL数据库连接管理器"""
    
    def __init__(self):
        self.connection = None
        self.is_connected = False
        
    def connect(self):
        """建立数据库连接"""
        try:
            self.connection = pymysql.connect(
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
            self.is_connected = True
            logger.info("Database connected successfully")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def disconnect(self):
        """断开数据库连接"""
        if self.connection:
            self.connection.close()
            self.is_connected = False
            logger.info("Database disconnected")
    
    @contextmanager
    def get_cursor(self):
        """获取数据库游标的上下文管理器"""
        if not self.is_connected:
            self.connect()
        
        cursor = None
        try:
            cursor = self.connection.cursor(pymysql.cursors.DictCursor)
            yield cursor
        except Exception as e:
            logger.error(f"Database cursor error: {e}")
            if self.connection:
                self.connection.rollback()
            raise
        finally:
            if cursor:
                cursor.close()
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """执行查询语句"""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()
    
    def execute_many(self, query: str, params: List[tuple]) -> int:
        """批量执行SQL语句"""
        with self.get_cursor() as cursor:
            affected_rows = cursor.executemany(query, params)
            self.connection.commit()
            return affected_rows
    
    def execute_update(self, query: str, params: Optional[tuple] = None) -> int:
        """执行更新语句"""
        with self.get_cursor() as cursor:
            affected_rows = cursor.execute(query, params)
            self.connection.commit()
            return affected_rows
    
    def insert_data(self, table: str, data: Dict[str, Any]) -> int:
        """插入数据"""
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        
        return self.execute_update(query, tuple(data.values()))
    
    def insert_many(self, table: str, data_list: List[Dict[str, Any]]) -> int:
        """批量插入数据"""
        if not data_list:
            return 0
            
        columns = list(data_list[0].keys())
        placeholders = ', '.join(['%s'] * len(columns))
        query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
        
        values = [tuple(data[col] for col in columns) for data in data_list]
        return self.execute_many(query, values)
    
    def insert_or_update(self, table: str, data: Dict[str, Any], unique_keys: List[str]) -> int:
        """插入或更新数据（ON DUPLICATE KEY UPDATE）"""
        columns = list(data.keys())
        placeholders = ', '.join(['%s'] * len(columns))
        
        # 构建ON DUPLICATE KEY UPDATE子句
        update_clause = ', '.join([f"{col} = VALUES({col})" for col in columns if col not in unique_keys])
        
        query = f"""
        INSERT INTO {table} ({', '.join(columns)}) 
        VALUES ({placeholders})
        ON DUPLICATE KEY UPDATE {update_clause}
        """
        
        return self.execute_update(query, tuple(data.values()))
    
    def update_data(self, table: str, data: Dict[str, Any], condition: str, params: tuple) -> int:
        """更新数据"""
        set_clause = ', '.join([f"{k} = %s" for k in data.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE {condition}"
        
        all_params = tuple(data.values()) + params
        return self.execute_update(query, all_params)
    
    def delete_data(self, table: str, condition: str, params: tuple) -> int:
        """删除数据"""
        query = f"DELETE FROM {table} WHERE {condition}"
        return self.execute_update(query, params)
    
    def table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        query = """
        SELECT COUNT(*) as count 
        FROM information_schema.tables 
        WHERE table_schema = %s AND table_name = %s
        """
        result = self.execute_query(query, (DB_CONFIG['database'], table_name))
        return result[0]['count'] > 0
    
    def get_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """获取表结构信息"""
        query = f"DESCRIBE {table_name}"
        return self.execute_query(query)
    
    def get_table_count(self, table_name: str, condition: str = "1=1", params: tuple = ()) -> int:
        """获取表记录数"""
        query = f"SELECT COUNT(*) as count FROM {table_name} WHERE {condition}"
        result = self.execute_query(query, params)
        return result[0]['count'] if result else 0
    
    def execute_transaction(self, queries: List[tuple]) -> bool:
        """执行事务"""
        try:
            with self.get_cursor() as cursor:
                for query, params in queries:
                    cursor.execute(query, params)
                self.connection.commit()
                return True
        except Exception as e:
            logger.error(f"Transaction failed: {e}")
            self.connection.rollback()
            return False


# 全局同步数据库连接实例
sync_db_connection = SyncDatabaseConnection()


def get_sync_db_connection() -> SyncDatabaseConnection:
    """获取同步数据库连接实例"""
    if not sync_db_connection.is_connected:
        sync_db_connection.connect()
    return sync_db_connection 