from typing import Dict, List, Any, Optional
from loguru import logger
from .db_config import DB_CONFIG
import json
import os
from enum import Enum
class BaseTableNames(Enum):
    stock_index = 'stock_index'
    stock_kline = 'stock_kline'

class BaseTableModel:
    """通用表操作模型基类"""
    
    def __init__(self, table_name: str, connected_db):
        self.db = connected_db
        self.table_name = table_name
        self.schema = self.load_schema()
        self.verbose = False
        # 默认为策略表（需要前缀）
        self.is_base_table = False

    def load_schema(self) -> dict:
        schema_path = os.path.join(os.path.dirname(__file__), 'tables', self.table_name, 'schema.json')
        schema = json.load(open(schema_path, 'r'))
        if not schema:
            logger.error(f"Failed to load schema from {schema_path} for table {self.table_name}")
            return None
        return schema
    
    def create_table(self, custom_table_name: str = None) -> bool:
        if not self.schema:
            logger.error(f"Failed to load schema for table: {self.table_name}")
            return False

        sql = self.to_create_table_sql(self.schema, custom_table_name)
        
        try:
            with self.db.get_sync_cursor() as cursor:
                cursor.execute(sql)
                logger.info(f"Table '{self.table_name}' is ready")
            return True
        except Exception as e:
            logger.error(f"Failed to create table {self.table_name}: {e}")
            return False


    def to_create_table_sql(self, schema_data: dict, custom_table_name: str = None):
        """根据schema数据生成CREATE TABLE SQL语句"""
        table_name = custom_table_name if custom_table_name else schema_data['name']
        primary_key = schema_data.get('primaryKey', 'id')
        fields = schema_data['fields']
        indexes = schema_data.get('indexes', [])
        
        # 构建字段定义
        field_definitions = []
        for field in fields:
            field_name = field['name']
            field_type = field['type'].upper()
            is_required = field.get('isRequired', False)
            auto_increment = field.get('autoIncrement', False)
            
            # 处理字段类型和长度
            if field_type == 'VARCHAR' and 'length' in field:
                field_def = f"`{field_name}` {field_type}({field['length']})"
            elif field_type == 'TEXT':
                field_def = f"`{field_name}` {field_type}"
            elif field_type == 'TINYINT':
                field_def = f"`{field_name}` {field_type}(1)"
            elif field_type == 'DATETIME':
                field_def = f"`{field_name}` {field_type}"
            elif field_type == 'DECIMAL' and 'length' in field:
                field_def = f"`{field_name}` {field_type}({field['length']})"
            elif field_type == 'BIGINT':
                field_def = f"`{field_name}` {field_type}"
            else:
                field_def = f"`{field_name}` {field_type}"
            
            # 添加约束
            if is_required:
                field_def += " NOT NULL"
            else:
                field_def += " NULL"
            
            # 添加自增约束
            if auto_increment:
                field_def += " AUTO_INCREMENT"
            
            field_definitions.append(field_def)
        
        # 添加主键约束
        if primary_key:
            if isinstance(primary_key, list):
                # 联合主键
                pk_fields = ', '.join([f"`{pk}`" for pk in primary_key])
                field_definitions.append(f"PRIMARY KEY ({pk_fields})")
            else:
                # 单字段主键
                field_definitions.append(f"PRIMARY KEY (`{primary_key}`)")
        
        # 添加索引
        for index in indexes:
            index_name = index['name']
            index_fields = ', '.join([f"`{field}`" for field in index['fields']])
            is_unique = index.get('unique', False)
            
            if is_unique:
                field_definitions.append(f"UNIQUE KEY `{index_name}` ({index_fields})")
            else:
                field_definitions.append(f"KEY `{index_name}` ({index_fields})")
        
        # 生成完整的CREATE TABLE语句
        field_definitions_str = ',\n            '.join(field_definitions)
        sql = f"""
        CREATE TABLE IF NOT EXISTS `{table_name}` (
            {field_definitions_str}
        ) ENGINE=InnoDB DEFAULT CHARSET={DB_CONFIG['base']['charset']} COLLATE={DB_CONFIG['base']['charset']}_general_ci;
        """
        return sql


    def clear(self) -> int:
        """清空表数据"""
        try:
            with self.db.get_sync_cursor() as cursor:
                cursor.execute(f"DELETE FROM {self.table_name}")
                cursor.connection.commit()
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Failed to clear table {self.table_name}: {e}")
            return 0
    
    def insert_one(self, data: Dict[str, Any]) -> int:
        """插入单条数据"""
        try:
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['%s'] * len(data))
            query = f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders})"
            
            with self.db.get_sync_cursor() as cursor:
                cursor.execute(query, tuple(data.values()))
                cursor.connection.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Failed to insert data into {self.table_name}: {e}")
            return 0
    
    def insert(self, data_list: List[Dict[str, Any]]) -> int:
        """批量插入数据"""
        if not data_list:
            return 0
        
        try:
            columns = list(data_list[0].keys())
            placeholders = ', '.join(['%s'] * len(columns))
            query = f"INSERT INTO {self.table_name} ({', '.join(columns)}) VALUES ({placeholders})"
            
            values = [tuple(data[col] for col in columns) for data in data_list]
            
            with self.db.get_sync_cursor() as cursor:
                cursor.executemany(query, values)
                cursor.connection.commit()
                return len(data_list)
        except Exception as e:
            logger.error(f"Failed to batch insert data into {self.table_name}: {e}")
            return 0
    
    def update_one(self, data: Dict[str, Any], condition: str, params: tuple = ()) -> int:
        """更新单条数据"""
        try:
            set_clause = ', '.join([f"{k} = %s" for k in data.keys()])
            query = f"UPDATE {self.table_name} SET {set_clause} WHERE {condition}"
            
            with self.db.get_sync_cursor() as cursor:
                cursor.execute(query, tuple(data.values()) + params)
                cursor.connection.commit()
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Failed to update data in {self.table_name}: {e}")
            return 0
    
    def update(self, data: Dict[str, Any], condition: str, params: tuple = ()) -> int:
        """更新数据（别名方法）"""
        return self.update_one(data, condition, params)
    
    def replace_one(self, data: Dict[str, Any], unique_keys: List[str]) -> int:
        """插入或更新单条数据"""
        try:
            # 构建ON DUPLICATE KEY UPDATE子句
            update_fields = [f"{k} = VALUES({k})" for k in data.keys() if k not in unique_keys]
            
            if not update_fields:
                # 如果没有需要更新的字段，就只做插入
                return self.insert_one(data)
            
            update_clause = ', '.join(update_fields)
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['%s'] * len(data))
            query = f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE {update_clause}"
            
            with self.db.get_sync_cursor() as cursor:
                cursor.execute(query, tuple(data.values()))
                cursor.connection.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Failed to upsert data in {self.table_name}: {e}")
            return 0
    
    def replace(self, data_list: List[Dict[str, Any]], unique_keys: List[str]) -> int:
        """
        批量插入或更新数据（支持线程安全）
        
        对于大数据量，自动使用异步写入队列
        对于小数据量，直接执行
        """
        if not data_list:
            return 0
        
        # 检查数据库管理器是否支持线程安全
        if hasattr(self.db, 'enable_thread_safety') and self.db.enable_thread_safety:
            # 对于大数据量，使用异步写入队列
            if len(data_list) > 1000:
                if self.db.is_verbose:
                    logger.info(f"Large dataset detected ({len(data_list)} records), using async write queue")
                
                # 定义回调函数
                def write_callback(result):
                    if self.db.is_verbose:
                        logger.info(f"Async write completed for {self.table_name}: {result} records")
                
                # 加入写入队列
                self.db.queue_write(self.table_name, data_list, unique_keys, write_callback)
                return len(data_list)
            
            # 对于小数据量，使用线程安全的批量写入
            try:
                # 构建SQL语句
                data_keys = list(data_list[0].keys())
                
                # 检查unique_keys是否都在data_keys中
                missing_keys = [k for k in unique_keys if k not in data_keys]
                if missing_keys:
                    logger.error(f"主键字段在数据中缺失: {missing_keys}")
                    return 0
                
                # 构建update子句
                update_fields = [k for k in data_keys if k not in unique_keys]
                update_clause = ', '.join([f"{k} = VALUES({k})" for k in update_fields])
                
                columns = ', '.join(data_keys)
                placeholders = ', '.join(['%s'] * len(data_keys))
                query = f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE {update_clause}"
                
                values = [tuple(data[col] for col in data_keys) for data in data_list]
                
                return self.db.execute_many(query, values)
                
            except Exception as e:
                logger.error(f"Failed to batch upsert data in {self.table_name}: {e}")
                return 0
        else:
            # 原有模式：使用重试机制
            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    # 构建ON DUPLICATE KEY UPDATE子句
                    data_keys = list(data_list[0].keys())
                    update_fields = [k for k in data_keys if k not in unique_keys]
                    update_clause = ', '.join([f"{k} = VALUES({k})" for k in update_fields])
                    
                    columns = ', '.join(data_keys)
                    placeholders = ', '.join(['%s'] * len(data_keys))
                    query = f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE {update_clause}"
                    
                    values = [tuple(data[col] for col in data_keys) for data in data_list]
                    
                    with self.db.get_sync_cursor() as cursor:
                        cursor.executemany(query, values)
                        cursor.connection.commit()
                        return len(data_list)
                        
                except Exception as e:
                    retry_count += 1
                    error_msg = str(e)
                    
                    # 如果是连接相关错误，尝试重试
                    if ("Packet sequence number wrong" in error_msg or 
                        "settimeout" in error_msg or 
                        "(0, '')" in error_msg):
                        
                        if retry_count < max_retries:
                            logger.warning(f"Database connection error, retrying ({retry_count}/{max_retries}): {e}")
                            import time
                            time.sleep(0.1 * retry_count)  # 指数退避
                            continue
                        else:
                            logger.error(f"Failed to batch upsert data in {self.table_name} after {max_retries} retries: {e}")
                            return 0
                    else:
                        # 其他错误，不重试
                        logger.error(f"Failed to batch upsert data in {self.table_name}: {e}")
                        return 0
            
            return 0
    
    def delete_one(self, condition: str, params: tuple = ()) -> int:
        """删除单条数据"""
        try:
            query = f"DELETE FROM {self.table_name} WHERE {condition} LIMIT 1"
            
            with self.db.get_sync_cursor() as cursor:
                cursor.execute(query, params)
                self.db.sync_connection.commit()
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Failed to delete data from {self.table_name}: {e}")
            return 0
    
    def delete(self, condition: str, params: tuple = ()) -> int:
        """删除数据"""
        try:
            query = f"DELETE FROM {self.table_name} WHERE {condition}"
            
            with self.db.get_sync_cursor() as cursor:
                cursor.execute(query, params)
                self.db.sync_connection.commit()
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Failed to delete data from {self.table_name}: {e}")
            return 0
    
    def load_one(self, condition: str = "1=1", params: tuple = (), order_by: str = None) -> Optional[Dict[str, Any]]:
        """查找单条记录"""
        try:
            query = f"SELECT * FROM {self.table_name} WHERE {condition}"
            if order_by:
                query += f" ORDER BY {order_by}"
            query += " LIMIT 1"
            
            result = self.db.execute_sync_query(query, params)
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Failed to load one record from {self.table_name}: {e}")
            return None
    
    def load_many(self, condition: str = "1=1", params: tuple = (), limit: int = None, order_by: str = None, offset: int = None) -> List[Dict[str, Any]]:
        """查找多条记录"""
        try:
            query = f"SELECT * FROM {self.table_name} WHERE {condition}"
            if order_by:
                query += f" ORDER BY {order_by}"
            if limit:
                query += f" LIMIT {limit}"
                if offset:
                    query += f" OFFSET {offset}"
            
            return self.db.execute_sync_query(query, params)
        except Exception as e:
            logger.error(f"Failed to load many records from {self.table_name}: {e}")
            return []

    def load_by_id(self, id_value: Any, id_field: str = "id") -> Optional[Dict[str, Any]]:
        """根据ID获取记录"""
        return self.load_one(f"{id_field} = %s", (id_value,))

    def load_all(self, order_by: str = None, limit: int = None) -> List[Dict[str, Any]]:
        """获取所有记录"""
        return self.load_many(order_by=order_by, limit=limit)

    def load_paginated(self, page: int = 1, page_size: int = 20, order_by: str = None) -> Dict[str, Any]:
        """分页获取记录"""
        offset = (page - 1) * page_size
        
        # 获取总数
        total = self.count()
        
        # 获取当前页数据
        data = self.load_many(limit=page_size, offset=offset, order_by=order_by)
        
        return {
            'data': data,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size
        }
    
    def count(self, condition: str = "1=1", params: tuple = ()) -> int:
        """统计记录数"""
        try:
            query = f"SELECT COUNT(*) as count FROM {self.table_name} WHERE {condition}"
            result = self.db.execute_sync_query(query, params)
            return result[0]['count'] if result else 0
        except Exception as e:
            logger.error(f"Failed to count records from {self.table_name}: {e}")
            return 0
    
    def exists(self, condition: str, params: tuple = ()) -> bool:
        """检查记录是否存在"""
        try:
            query = f"SELECT 1 FROM {self.table_name} WHERE {condition} LIMIT 1"
            result = self.db.execute_sync_query(query, params)
            return len(result) > 0
        except Exception as e:
            logger.error(f"Failed to check existence in {self.table_name}: {e}")
            return False
    

    
    def execute_raw_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """执行原始SQL查询"""
        try:
            return self.db.execute_sync_query(query, params)
        except Exception as e:
            logger.error(f"Failed to execute raw query: {e}")
            return []
    
    def execute_raw_update(self, query: str, params: tuple = ()) -> int:
        """执行原始SQL更新"""
        try:
            with self.db.get_sync_cursor() as cursor:
                cursor.execute(query, params)
                cursor.connection.commit()
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Failed to execute raw update: {e}")
            return 0
    
    def wait_for_writes(self):
        """等待所有异步写入完成"""
        if hasattr(self.db, 'wait_for_writes'):
            self.db.wait_for_writes()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        if hasattr(self.db, 'get_stats'):
            return self.db.get_stats()
        return {}