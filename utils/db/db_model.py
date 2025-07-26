from typing import Dict, List, Any, Optional
from loguru import logger
from .config import DB_CONFIG
import json
import os

class BaseTableModel:
    """通用表操作模型基类"""
    
    def __init__(self, table_name: str, table_type: str, connected_db):
        self.db = connected_db
        self.table_name = table_name
        self.table_type = table_type
        self.schema_path = os.path.join(os.path.dirname(__file__), 'tables', table_type, table_name, 'schema.json')
        
    
    def get_table_name(self) -> str:
        return self.table_name
    
    def create_table(self) -> bool:
        schema_data = self.load_table_schema()
        if not schema_data:
            logger.error(f"Failed to load schema for table: {self.table_name}")
            return False

        sql = self.to_create_table_sql(schema_data)
        
        try:
            with self.db.sync_connection.cursor() as cursor:
                cursor.execute(sql)
                logger.info(f"Table '{self.table_name}' is ready")
            self.db.sync_connection.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to create table {self.table_name}: {e}")
            return False

    def load_table_schema(self):
        if not os.path.exists(self.schema_path):
            logger.error(f"Schema file not found: {self.schema_path}")
            return None
        
        # 读取schema文件
        with open(self.schema_path, 'r', encoding='utf-8') as f:
            schema_data = json.load(f)
        
        return schema_data

    def to_create_table_sql(self, schema_data: dict):
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
                self.db.sync_connection.commit()
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
                self.db.sync_connection.commit()
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
                self.db.sync_connection.commit()
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
                self.db.sync_connection.commit()
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Failed to update data in {self.table_name}: {e}")
            return 0
    
    def update(self, data: Dict[str, Any], condition: str, params: tuple = ()) -> int:
        """更新数据（别名方法）"""
        return self.update_one(data, condition, params)
    
    def upsert_one(self, data: Dict[str, Any], unique_keys: List[str]) -> int:
        """插入或更新单条数据"""
        try:
            # 构建ON DUPLICATE KEY UPDATE子句
            update_clause = ', '.join([f"{k} = VALUES({k})" for k in data.keys() if k not in unique_keys])
            
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['%s'] * len(data))
            query = f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE {update_clause}"
            
            with self.db.get_sync_cursor() as cursor:
                cursor.execute(query, tuple(data.values()))
                self.db.sync_connection.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Failed to upsert data in {self.table_name}: {e}")
            return 0
    
    def upsert(self, data_list: List[Dict[str, Any]], unique_keys: List[str]) -> int:
        """批量插入或更新数据"""
        if not data_list:
            return 0
        
        try:
            # 构建ON DUPLICATE KEY UPDATE子句
            update_clause = ', '.join([f"{k} = VALUES({k})" for k in data_list[0].keys() if k not in unique_keys])
            
            columns = list(data_list[0].keys())
            placeholders = ', '.join(['%s'] * len(columns))
            query = f"INSERT INTO {self.table_name} ({', '.join(columns)}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE {update_clause}"
            
            values = [tuple(data[col] for col in columns) for data in data_list]
            
            with self.db.get_sync_cursor() as cursor:
                cursor.executemany(query, values)
                self.db.sync_connection.commit()
                return len(data_list)
        except Exception as e:
            logger.error(f"Failed to batch upsert data in {self.table_name}: {e}")
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
    
    def find_one(self, condition: str = "1=1", params: tuple = (), order_by: str = None) -> Optional[Dict[str, Any]]:
        """查找单条记录"""
        try:
            query = f"SELECT * FROM {self.table_name} WHERE {condition}"
            if order_by:
                query += f" ORDER BY {order_by}"
            query += " LIMIT 1"
            
            result = self.db.execute_sync_query(query, params)
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Failed to find one record from {self.table_name}: {e}")
            return None
    
    def find_many(self, condition: str = "1=1", params: tuple = (), limit: int = None, order_by: str = None, offset: int = None) -> List[Dict[str, Any]]:
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
            logger.error(f"Failed to find many records from {self.table_name}: {e}")
            return []
    
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
    
    def get_by_id(self, id_value: Any, id_field: str = "id") -> Optional[Dict[str, Any]]:
        """根据ID获取记录"""
        return self.find_one(f"{id_field} = %s", (id_value,))
    
    def get_all(self, order_by: str = None, limit: int = None) -> List[Dict[str, Any]]:
        """获取所有记录"""
        return self.find_many(order_by=order_by, limit=limit)
    
    def get_paginated(self, page: int = 1, page_size: int = 20, order_by: str = None) -> Dict[str, Any]:
        """分页获取记录"""
        offset = (page - 1) * page_size
        
        # 获取总数
        total = self.count()
        
        # 获取当前页数据
        data = self.find_many(limit=page_size, offset=offset, order_by=order_by)
        
        return {
            'data': data,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size
        }
    
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
                self.db.sync_connection.commit()
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Failed to execute raw update: {e}")
            return 0