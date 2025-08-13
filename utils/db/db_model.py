from typing import Dict, List, Any, Optional
from loguru import logger

from utils.db.db_service import DBService
from .db_config import DB_CONFIG
import json
import os


class BaseTableModel:
    """通用表操作模型基类"""
    
    def __init__(self, table_name: str, connected_db):
        self.db = connected_db
        self.table_name = table_name
        self.schema = self.load_schema()
        self.verbose = False
        # 默认为策略表（需要前缀）
        self.is_base_table = False

    # ***********************************
    #        table operations
    # ***********************************
    
    def load_schema(self) -> dict:
        schema_path = os.path.join(os.path.dirname(__file__), 'tables', self.table_name, 'schema.json')
        schema = json.load(open(schema_path, 'r'))
        if not schema:
            logger.error(f"Failed to load schema from {schema_path} for table {self.table_name}")
            return None
        return schema
    
    def create_table(self, custom_table_name: str = None) -> None:
        if not self.schema:
            logger.error(f"Failed create table: {self.table_name}, because schema is not found")
            return

        sql = DBService.parse_db_schema(self.schema, custom_table_name)

        with self.db.get_sync_cursor() as cursor:
            cursor.execute(sql)
            # 只在详细模式下输出日志，减少重复日志
            if self.db.is_verbose:
                logger.info(f"Table '{self.table_name}' is ready")

    def drop_table(self) -> None:
        with self.db.get_sync_cursor() as cursor:
            cursor.execute(f"DROP TABLE IF EXISTS {self.table_name}")
            cursor.connection.commit()
            if self.db.is_verbose:
                logger.info(f"Table '{self.table_name}' is dropped")


    def clear_table(self) -> int:
        """清空表数据"""
        with self.db.get_sync_cursor() as cursor:
            cursor.execute(f"DELETE FROM {self.table_name}")
            cursor.connection.commit()
            return cursor.rowcount

    # ***********************************
    #        data count & exists operations
    # ***********************************
    
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
        return self.count(condition, params) > 0

    # ***********************************
    #        data get operations
    # ***********************************

    # 使用 params 的安全方式
    # condition = "stock_code = ? AND price > ?"
    # params = ("000001", 10.0)
    # records = db_model.load(condition=condition, params=params)

    def load(self, condition: str = "1=1", params: tuple = (), order_by: str = None, limit: int = None, offset: int = None) -> List[Dict[str, Any]]:
        """查找记录"""
        query = f"SELECT * FROM {self.table_name} WHERE {condition}"
        if order_by:
            query += f" ORDER BY {order_by}"
        if limit:
            query += f" LIMIT {limit}"
        if offset:
            query += f" OFFSET {offset}"
        try:
            return self.db.execute_sync_query(query, params)
        except Exception as e:
            logger.error(f"Failed to load records from {self.table_name}: {e}")
            return []

    def load_one(self, condition: str = "1=1", params: tuple = (), order_by: str = None) -> Optional[Dict[str, Any]]:
        result = self.load(condition, params, order_by, limit=1)
        return result[0] if result else None

    def load_all(self, condition: str = "1=1", params: tuple = (), order_by: str = None) -> List[Dict[str, Any]]:
        return self.load(condition, params, order_by)
    
    def load_many(self, condition: str = "1=1", params: tuple = (), limit: int = None, order_by: str = None, offset: int = None) -> List[Dict[str, Any]]:
        return self.load(condition, params, order_by, limit, offset)

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


    # ***********************************
    #        data delete operations
    # ***********************************
    
    def delete(self, condition: str, params: tuple = (), limit: int = None) -> int:
        """删除数据（带重试机制）"""
        max_retries = 3
        retry_delay = 0.1
        
        for attempt in range(max_retries):
            try:
                query = f"DELETE FROM {self.table_name} WHERE {condition}"
                if limit:
                    query += f" LIMIT {limit}"
                
                with self.db.get_sync_cursor() as cursor:
                    cursor.execute(query, params)
                    cursor.connection.commit()
                    return cursor.rowcount
            except Exception as e:
                logger.error(f"Failed to delete data from {self.table_name} (attempt {attempt + 1}/{max_retries}): {e}")
                
                if attempt == max_retries - 1:
                    return 0  # 最后一次尝试失败，返回0
                
                # 等待后重试
                import time
                time.sleep(retry_delay * (2 ** attempt))
                continue
        
        return 0

    def delete_one(self, condition: str, params: tuple = ()) -> int:
        """删除单条数据"""
        return self.delete(condition, params, 1)




    # ***********************************
    #        data insert & update operations
    # ***********************************

    def insert(self, data_list: List[Dict[str, Any]]) -> int:
        """批量插入数据"""
        if not data_list:
            return 0
        
        try:
            columns, placeholders = DBService.to_columns_and_values(data_list)
            query = f"INSERT INTO {self.table_name} ({', '.join(columns)}) VALUES ({placeholders})"
            
            # 构建值列表
            values = [tuple(data[col] for col in columns) for data in data_list]
            
            with self.db.get_sync_cursor() as cursor:
                cursor.executemany(query, values)
                cursor.connection.commit()
                return len(data_list)
        except Exception as e:
            logger.error(f"Failed to batch insert data into {self.table_name}: {e}")
            return 0
    

    def insert_one(self, data: Dict[str, Any]) -> int:
        """插入单条数据"""
        return self.insert([data])

    def update(self, data: Dict[str, Any], condition: str, params: tuple = ()) -> int:
        """更新数据（别名方法）"""
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


    # ***********************************
    #        data upsert operations
    # ***********************************
    def replace(self, data_list: List[Dict[str, Any]], unique_keys: List[str]) -> int:
        """
        批量插入或更新数据（支持线程安全）
        
        对于大数据量，自动使用异步写入队列
        对于小数据量，直接执行
        """
        if not data_list:
            return 0
        
        # 检查数据库管理器是否支持线程安全
        if DB_CONFIG['thread_safety']['enable']:
            # 对于大数据量，使用异步写入队列
            if len(data_list) > DB_CONFIG['thread_safety']['turn_to_batch_threshold']:
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
                columns, values, update_clause = DBService.to_upsert_params(data_list, unique_keys)

                query = f"INSERT INTO {self.table_name} ({', '.join(columns)}) VALUES ({', '.join(['%s'] * len(columns))}) ON DUPLICATE KEY UPDATE {update_clause}"
                with self.db.get_sync_cursor() as cursor:
                    cursor.executemany(query, values)
                    cursor.connection.commit()
                    return len(data_list)
                
            except Exception as e:
                logger.error(f"Failed to batch upsert data in {self.table_name}: {e}")
                return 0
        else:
            # 原有模式：使用重试机制
            retry_count = 0
            max_retries = DB_CONFIG['thread_safety']['max_retries']
            
            while retry_count < max_retries:
                try:
                    # 构建ON DUPLICATE KEY UPDATE子句
                    columns, values, update_clause = DBService.to_upsert_params(data_list, unique_keys)
                    
                    query = f"INSERT INTO {self.table_name} ({', '.join(columns)}) VALUES ({', '.join(['%s'] * len(columns))}) ON DUPLICATE KEY UPDATE {update_clause}"
                    
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
    
    def replace_one(self, data: Dict[str, Any], unique_keys: List[str]) -> int:
        """插入或更新单条数据"""
        return self.replace([data], unique_keys)
    
    
    # ***********************************
    #        support raw query operations
    # ***********************************
    def execute_raw_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """执行原始SQL查询"""
        try:
            return self.db.execute_sync_query(query, params)
        except Exception as e:
            logger.error(f"Failed to execute raw query: {e}")
            return []

    def execute_raw_update(self, query: str, params: tuple = ()) -> int:
        """执行原始SQL更新语句"""
        try:
            with self.db.get_sync_cursor() as cursor:
                cursor.execute(query, params)
                cursor.connection.commit()
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Failed to execute raw update: {e}")
            return 0


    # ***********************************
    #        others
    # ***********************************
    def wait_for_writes(self):
        """等待所有异步写入完成"""
        if hasattr(self.db, 'wait_for_writes'):
            self.db.wait_for_writes()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        if hasattr(self.db, 'get_stats'):
            return self.db.get_stats()
        return {}
