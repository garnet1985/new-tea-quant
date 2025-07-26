"""
Unified MySQL Database Manager
支持同步和异步操作
"""
import json
import pymysql
import asyncio
from typing import Optional, Dict, List, Any
from contextlib import contextmanager
from loguru import logger
from .config import DB_CONFIG, TABLES, STRATEGY_TABLES, TABLE_SCHEMA_PATH


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

    def initialize(self):
        """初始化同步数据库连接"""
        self.connect_sync()
        self.create_db()
        self.create_tables()
        self.create_indexes()
    
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
        except pymysql.err.OperationalError as e:
            # 检查是否是数据库不存在的错误
            if e.args[0] == 1049:  # Unknown database
                logger.warning(f"Database '{DB_CONFIG['base']['database']}' does not exist, creating it...")
                if self.create_db():
                    # 重新尝试连接
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
                    logger.info("Synchronous database connected successfully after creation")
                else:
                    logger.error("Failed to create database")
                    raise
            else:
                logger.error(f"Failed to connect to database synchronously: {e}")
                raise
        except Exception as e:
            logger.error(f"Failed to connect to database synchronously: {e}")
            raise
    
    def disconnect_sync(self):
        """断开同步数据库连接"""
        if self.sync_connection:
            self.sync_connection.close()
            self.is_sync_connected = False
            logger.info("Synchronous database disconnected")

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
                logger.info(f"Database '{DB_CONFIG['base']['database']}' is ready")
            
            temp_connection.close()
            return True
            
        except Exception as e:
            logger.error(f"Failed to create database: {e}")
            return False 

    
    def create_tables(self):
        """创建基础表（如果不存在）"""
        # 确保已连接到数据库
        if not self.is_sync_connected:
            self.connect_sync()
            
        # 使用schema驱动的表创建
        base_tables = TABLES
        strategy_tables = STRATEGY_TABLES
        
        for table_name in base_tables:
            self.create_table(table_name)
        
        for table_name in strategy_tables:
            self.create_table(table_name)
            

    def create_table(self, table_name: str):
        """根据schema.json创建表"""
        schema = self.load_table_schema(table_name)
        if not schema:
            logger.error(f"Failed to load schema for table: {table_name}")
            return

        with self.sync_connection.cursor() as cursor:
            cursor.execute(schema)
            logger.info(f"Table '{table_name}' is ready")
        self.sync_connection.commit()

    
    def load_table_schema(self, table_name: str) -> str:
        """加载表结构并生成CREATE TABLE语句"""
        import json
        import os
        
        try:
            # 判断是基础表还是策略表
            if table_name in TABLES:
                # 基础表
                schema_path = os.path.join(
                    os.path.dirname(__file__), 
                    'tables', 'base', table_name, 'schema.json'
                )
            elif table_name in STRATEGY_TABLES:
                # 策略表
                schema_path = os.path.join(
                    os.path.dirname(__file__), 
                    'tables', 'strategy', table_name, 'schema.json'
                )
            else:
                logger.error(f"Table '{table_name}' not found in TABLES or STRATEGY_TABLES")
                return None
            
            if not os.path.exists(schema_path):
                logger.error(f"Schema file not found: {schema_path}")
                return None
            
            # 读取schema文件
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema_data = json.load(f)
            
            # 生成CREATE TABLE语句
            return self._generate_create_table_sql(schema_data)
            
        except Exception as e:
            logger.error(f"Failed to load schema for {table_name}: {e}")
            return None
    
    def _generate_create_table_sql(self, schema_data: dict) -> str:
        """根据schema数据生成CREATE TABLE SQL语句"""
        table_name = schema_data['name']
        primary_key = schema_data.get('primaryKey', 'id')
        fields = schema_data['fields']
        
        # 构建字段定义
        field_definitions = []
        for field in fields:
            field_name = field['name']
            field_type = field['type'].upper()
            is_required = field.get('isRequired', False)
            
            # 处理字段类型和长度
            if field_type == 'VARCHAR' and 'length' in field:
                field_def = f"`{field_name}` {field_type}({field['length']})"
            elif field_type == 'TEXT':
                field_def = f"`{field_name}` {field_type}"
            elif field_type == 'TINYINT':
                field_def = f"`{field_name}` {field_type}(1)"
            elif field_type == 'DATETIME':
                field_def = f"`{field_name}` {field_type}"
            else:
                field_def = f"`{field_name}` {field_type}"
            
            # 添加约束
            if is_required:
                field_def += " NOT NULL"
            else:
                field_def += " NULL"
            
            field_definitions.append(field_def)
        
        # 添加主键约束
        if primary_key and primary_key != 'id':
            field_definitions.append(f"PRIMARY KEY (`{primary_key}`)")
        
        # 生成完整的CREATE TABLE语句
        field_definitions_str = ',\n            '.join(field_definitions)
        create_sql = f"""
        CREATE TABLE IF NOT EXISTS `{table_name}` (
            {field_definitions_str}
        ) ENGINE=InnoDB DEFAULT CHARSET={DB_CONFIG['base']['charset']} COLLATE={DB_CONFIG['base']['charset']}_general_ci;
        """
        
        return create_sql
    
    def create_indexes(self):
        pass
        # """创建索引（如果不存在）"""
        # try:
        #     if not self.is_sync_connected:
        #         self.connect_sync()
            
        #     # 为stock_index表创建索引
        #     indexes = [
        #         "CREATE INDEX IF NOT EXISTS idx_stock_index_market ON stock_index(market)",
        #         "CREATE INDEX IF NOT EXISTS idx_stock_index_industry ON stock_index(industry)",
        #         "CREATE INDEX IF NOT EXISTS idx_stock_index_type ON stock_index(type)",
        #     ]
            
        #     with self.get_sync_cursor() as cursor:
        #         for index_sql in indexes:
        #             try:
        #                 cursor.execute(index_sql)
        #                 logger.info(f"Index created: {index_sql}")
        #             except Exception as e:
        #                 logger.warning(f"Failed to create index: {e}")
            
        #     return True
            
        # except Exception as e:
        #     logger.error(f"Failed to create indexes: {e}")
        #     return False

    
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
    
    # def execute_sync_many(self, query: str, params: List[tuple]) -> int:
    #     """批量执行同步SQL语句"""
    #     with self.get_sync_cursor() as cursor:
    #         affected_rows = cursor.executemany(query, params)
    #         self.sync_connection.commit()
    #         return affected_rows
    
    # def execute_sync_update(self, query: str, params: Optional[tuple] = None) -> int:
    #     """执行同步更新语句"""
    #     with self.get_sync_cursor() as cursor:
    #         affected_rows = cursor.execute(query, params)
    #         self.sync_connection.commit()
    #         return affected_rows
    
    # def insert_sync_data(self, table: str, data: Dict[str, Any]) -> int:
    #     """同步插入数据"""
    #     columns = ', '.join(data.keys())
    #     placeholders = ', '.join(['%s'] * len(data))
    #     query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        
    #     return self.execute_sync_update(query, tuple(data.values()))
    
    # def insert_sync_many(self, table: str, data_list: List[Dict[str, Any]]) -> int:
    #     """同步批量插入数据"""
    #     if not data_list:
    #         return 0
            
    #     columns = list(data_list[0].keys())
    #     placeholders = ', '.join(['%s'] * len(columns))
    #     query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
        
    #     values = [tuple(data[col] for col in columns) for data in data_list]
    #     return self.execute_sync_many(query, values)
    
    # # ==================== 异步连接方法 ====================
    
    # async def initialize_async(self):
    #     """初始化异步数据库连接池"""
    #     try:
    #         # 创建异步连接池
    #         self.async_pool = await self._create_async_connection_pool()
    #         self.is_async_initialized = True
    #         logger.info("Asynchronous database connection pool initialized successfully")
    #     except Exception as e:
    #         logger.error(f"Failed to initialize asynchronous database connection pool: {e}")
    #         raise
    
    # async def _create_async_connection_pool(self):
    #     """创建异步连接池"""
    #     return await pymysql.connect(
    #         host=DB_CONFIG['base']['host'],
    #         user=DB_CONFIG['base']['user'],
    #         password=DB_CONFIG['base']['password'],
    #         database=DB_CONFIG['base']['database'],
    #         port=DB_CONFIG['base']['port'],
    #         charset=DB_CONFIG['base']['charset'],
    #         autocommit=DB_CONFIG['base']['autocommit'],
    #         max_allowed_packet=16777216,  # 16MB
    #         connect_timeout=DB_CONFIG['pool']['connection_timeout'],
    #         read_timeout=DB_CONFIG['pool']['read_timeout'],
    #         write_timeout=DB_CONFIG['pool']['write_timeout'],
    #     )
    
    # async def get_async_connection(self):
    #     """获取异步数据库连接"""
    #     if not self.is_async_initialized:
    #         await self.initialize_async()
    #     return self.async_pool
    
    # async def execute_async_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
    #     """执行异步查询语句"""
    #     connection = await self.get_async_connection()
    #     async with connection.cursor(pymysql.cursors.DictCursor) as cursor:
    #         await cursor.execute(query, params)
    #         result = await cursor.fetchall()
    #         return result
    
    # async def execute_async_update(self, query: str, params: Optional[tuple] = None) -> int:
    #     """执行异步更新语句"""
    #     connection = await self.get_async_connection()
    #     async with connection.cursor() as cursor:
    #         affected_rows = await cursor.execute(query, params)
    #         await connection.commit()
    #         return affected_rows
    
    # async def insert_async_data(self, table: str, data: Dict[str, Any]) -> int:
    #     """异步插入数据"""
    #     columns = ', '.join(data.keys())
    #     placeholders = ', '.join(['%s'] * len(data))
    #     query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        
    #     return await self.execute_async_update(query, tuple(data.values()))
    
    # ==================== 通用工具方法 ====================
    
    # def table_exists_sync(self, table_name: str) -> bool:
    #     """同步检查表是否存在"""
    #     query = """
    #     SELECT COUNT(*) as count 
    #     FROM information_schema.tables 
    #     WHERE table_schema = %s AND table_name = %s
    #     """
    #     result = self.execute_sync_query(query, (DB_CONFIG['base']['database'], table_name))
    #     return result[0]['count'] > 0
    
    # async def table_exists_async(self, table_name: str) -> bool:
    #     """异步检查表是否存在"""
    #     query = """
    #     SELECT COUNT(*) as count 
    #     FROM information_schema.tables 
    #     WHERE table_schema = %s AND table_name = %s
    #     """
    #     result = await self.execute_async_query(query, (DB_CONFIG['base']['database'], table_name))
    #     return result[0]['count'] > 0
    
    # def get_table_info_sync(self, table_name: str) -> List[Dict[str, Any]]:
    #     """同步获取表结构信息"""
    #     query = f"DESCRIBE {table_name}"
    #     return self.execute_sync_query(query)
    
    # async def get_table_info_async(self, table_name: str) -> List[Dict[str, Any]]:
    #     """异步获取表结构信息"""
    #     query = f"DESCRIBE {table_name}"
    #     return await self.execute_async_query(query)
    
    # def get_table_count_sync(self, table_name: str, condition: str = "1=1", params: tuple = ()) -> int:
    #     """同步获取表记录数"""
    #     query = f"SELECT COUNT(*) as count FROM {table_name} WHERE {condition}"
    #     result = self.execute_sync_query(query, params)
    #     return result[0]['count'] if result else 0
    
    # async def get_table_count_async(self, table_name: str, condition: str = "1=1", params: tuple = ()) -> int:
    #     """异步获取表记录数"""
    #     query = f"SELECT COUNT(*) as count FROM {table_name} WHERE {condition}"
    #     result = await self.execute_async_query(query, params)
    #     return result[0]['count'] if result else 0
    
    # def execute_sync_transaction(self, queries: List[tuple]) -> bool:
    #     """执行同步事务"""
    #     try:
    #         with self.get_sync_cursor() as cursor:
    #             for query, params in queries:
    #                 cursor.execute(query, params)
    #             self.sync_connection.commit()
    #             return True
    #     except Exception as e:
    #         logger.error(f"Synchronous transaction failed: {e}")
    #         self.sync_connection.rollback()
    #         return False
    
    # async def execute_async_transaction(self, queries: List[tuple]) -> bool:
    #     """执行异步事务"""
    #     try:
    #         connection = await self.get_async_connection()
    #         async with connection.cursor() as cursor:
    #             for query, params in queries:
    #                 await cursor.execute(query, params)
    #             await connection.commit()
    #             return True
    #     except Exception as e:
    #         logger.error(f"Asynchronous transaction failed: {e}")
    #         await connection.rollback()
    #         return False
    
    # # ==================== 兼容性方法 ====================
    
    # # 为了保持向后兼容，提供一些别名方法
    # def connect(self):
    #     """兼容性方法：建立同步连接"""
    #     return self.connect_sync()
    
    # def disconnect(self):
    #     """兼容性方法：断开同步连接"""
    #     return self.disconnect_sync()
    
    # @contextmanager
    # def get_cursor(self):
    #     """兼容性方法：获取同步游标"""
    #     return self.get_sync_cursor()
    
    # def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
    #     """兼容性方法：执行同步查询"""
    #     return self.execute_sync_query(query, params)
    
    # def execute_many(self, query: str, params: List[tuple]) -> int:
    #     """兼容性方法：批量执行同步SQL"""
    #     return self.execute_sync_many(query, params)
    
    # def execute_update(self, query: str, params: Optional[tuple] = None) -> int:
    #     """兼容性方法：执行同步更新"""
    #     return self.execute_sync_update(query, params)
    
    # def insert_data(self, table: str, data: Dict[str, Any]) -> int:
    #     """兼容性方法：同步插入数据"""
    #     return self.insert_sync_data(table, data)
    
    # def insert_many(self, table: str, data_list: List[Dict[str, Any]]) -> int:
    #     """兼容性方法：同步批量插入数据"""
    #     return self.insert_sync_many(table, data_list)
    
    # # ==================== 数据库管理方法 ====================
    
    

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