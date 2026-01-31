"""
DbBaseModel - 数据库表操作的通用基类

这是一个纯粹的工具类，封装了常见的数据库表操作，提供：
- 基础 CRUD（增删改查）
- 统计行数（count，支持 WHERE 条件）
- 分页查询
- 时序数据特有的查询（最新日期、最新记录等）
- Upsert（插入或更新）
- 批量操作
- 重试机制

特点：
- 基于 JSON Schema 自动创建表
- 支持参数化查询（防 SQL 注入）
- 针对时序数据优化
- 性能优先（直接 SQL，无 ORM 开销）

使用方式：
    # 方式 1: 直接使用（简单场景）
    from core.infra.db import DbBaseModel
    from core.infra.db import DatabaseManager
    
    db = DatabaseManager()
    db.initialize()
    
    model = DbBaseModel('stock_kline', db)
    records = model.load("id = %s", ('000001.SZ',))
    
    # 方式 2: 继承使用（推荐，业务场景）
    class StockKlineModel(DbBaseModel):
        def __init__(self, db=None):
            super().__init__('stock_kline', db)
        
        def load_by_date_range(self, stock_id, start_date, end_date):
            return self.load(
                "id = %s AND date BETWEEN %s AND %s",
                (stock_id, start_date, end_date),
                order_by="date ASC"
            )

更新日期：2024-12-04
"""
import math
from typing import Dict, List, Any, Optional
from loguru import logger
import json
import os

from core.infra.db.helpers.db_helpers import DBHelper
from core.infra.db.table_queriers.query_helpers import TimeSeriesHelper, DataFrameHelper, SchemaFormatter
from core.infra.db.table_queriers.services.batch_operation import BatchOperation


class DbBaseModel(TimeSeriesHelper, DataFrameHelper):
    """
    通用表操作模型基类
    
    所有基础表的 Model 类都继承自此类，提供单表的 CRUD 操作。
    此类是 core/infra/db 模块的核心组件之一，由 DataManager 和 DataService 内部使用。
    """
    
    def __init__(self, table_name: str, db=None):
        """
        初始化表模型
        
        Args:
            table_name: 表名
            db: DatabaseManager实例（可选）
                - 如果不传入，自动使用默认实例
                - 如果默认实例不存在，自动创建并初始化（多进程安全）
                - 如果传入，使用指定实例（测试场景）
        """
        from core.infra.db import DatabaseManager
        
        # 自动获取或使用传入的 db
        if db is not None:
            self.db = db
        else:
            # 自动获取默认实例（如果不存在会自动创建并初始化）
            self.db = DatabaseManager.get_default(auto_init=True)
        self.table_name = table_name
        self.schema = self.load_schema()
        self.verbose = False
        # 默认为策略表（需要前缀）
        self.is_base_table = False

    # ***********************************
    #        table operations
    # ***********************************
    
    def load_schema(self) -> dict:
        """
        加载表的 schema
        
        优先从 app/core/modules/data_manager/base_tables 加载，
        如果不存在则尝试从策略自定义表加载
        
        使用 SchemaManager 统一加载逻辑
        """
        from core.infra.db.schema_management.schema_manager import SchemaManager
        
        # 使用 SchemaManager 加载 schema
        schema_manager = SchemaManager()
        schema = schema_manager.get_table_schema(self.table_name)
        
        if schema:
            return schema
        
        # 如果不存在，可能是策略自定义表（暂不处理）
        logger.warning(f"Schema not found for table {self.table_name}")
        return None


    def create_table(self, custom_table_name: str = None) -> None:
        if not self.schema:
            logger.error(f"Failed create table: {self.table_name}, because schema is not found")
            return

        # 使用 SchemaManager 生成 SQL
        from core.infra.db.schema_management.schema_manager import SchemaManager
        schema_manager = SchemaManager(database_type=self.db.config.get('database_type', 'postgresql'))
        
        # 如果有自定义表名，修改 schema
        schema_to_use = self.schema.copy()
        if custom_table_name:
            schema_to_use['name'] = custom_table_name
        
        sql = schema_manager.generate_create_table_sql(schema_to_use)

        with self.db.get_sync_cursor() as cursor:
            cursor.execute(sql)
            # 只在详细模式下输出日志，减少重复日志
            if self.db.is_verbose:
                logger.info(f"Table '{self.table_name}' is ready")

    def drop_table(self) -> None:
        with self.db.get_sync_cursor() as cursor:
            cursor.execute(f"DROP TABLE IF EXISTS {self.table_name}")
            if self.db.is_verbose:
                logger.info(f"Table '{self.table_name}' is dropped")


    def clear_table(self) -> int:
        """清空表数据"""
        with self.db.get_sync_cursor() as cursor:
            cursor.execute(f"DELETE FROM {self.table_name}")
            return cursor.rowcount

    def describe(self, output: bool = True) -> str:
        """
        打印表结构和描述
        
        Args:
            output: 是否直接打印到控制台（默认 True）
            
        Returns:
            格式化的表结构描述字符串
        """
        return SchemaFormatter.format_table_description(self.schema, self.table_name, output)

    # ***********************************
    #        data count & exists operations
    # ***********************************

    def count(self, condition: str = "1=1", params: tuple = ()) -> int:
        """
        统计表记录数（支持条件过滤）。

        Args:
            condition: WHERE 条件，默认 "1=1" 表示全表统计。须使用占位符时用 %s，与 params 配合。
            params: 条件参数元组，与 condition 中的 %s 一一对应。

        Returns:
            int: 满足条件的行数；表不存在或查询失败时返回 0。

        示例:
            model.count()                    # 全表行数
            model.count("term = %s", ("daily",))  # term=daily 的行数
        """
        try:
            query = f"SELECT COUNT(*) AS cnt FROM {self.table_name} WHERE {condition}"
            result = self.db.execute_sync_query(query, params)
            if not result or len(result) == 0:
                return 0
            row = result[0]
            # 兼容不同驱动返回的列名（cnt / count / COUNT 等）
            n = row.get("cnt") if "cnt" in row else row.get("count", 0)
            if n is None:
                return 0
            return int(n)
        except Exception as e:
            logger.error(f"Failed to count records from {self.table_name}: {e}")
            return 0

    def is_exists(self, condition: str, params: tuple = ()) -> bool:
        """检查记录是否存在"""
        return self.count(condition, params) > 0

    # ***********************************
    #        data get operations
    # ***********************************

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
    
    
    def load_latest_records(self, date_field: str = None, primary_keys: List[str] = None) -> List[Dict[str, Any]]:
        """
        加载每个主键分组中最新日期的记录
        
        用于增量更新时获取各股票/各实体的最新数据
        
        Args:
            date_field: 日期字段名（如果为None，从schema中自动获取）
            primary_keys: 主键列表（如果为None，从schema中自动获取）
            
        Returns:
            List[Dict]: 最新记录列表
            
        Raises:
            ValueError: 如果日期字段或主键未找到
            
        示例：
            # 股票K线表：返回每个股票的最新K线记录
            # 主键: ['id', 'date']
            # 返回: [{id: '000001.SZ', date: '20240101', ...}, ...]
        """
        if date_field is None:
            date_field = self._get_date_field_from_schema()
        
        if primary_keys is None:
            primary_keys = self._get_primary_keys_from_schema()
        
        # 过滤掉日期字段（日期字段不用于分组）
        group_keys = [k for k in primary_keys if k != date_field]
        
        if not group_keys:
            # 没有分组键，返回最新的一条记录
            latest_record = self.load_one("1=1", order_by=f"{date_field} DESC")
            return [latest_record] if latest_record else []
        
        # 有分组键，查询每个分组的最新记录
        group_keys_str = ', '.join(group_keys)
        query = f"""
            SELECT t1.* 
            FROM {self.table_name} t1
            INNER JOIN (
                SELECT {group_keys_str}, MAX({date_field}) as max_date
                FROM {self.table_name}
                GROUP BY {group_keys_str}
            ) t2 
            ON {' AND '.join([f't1.{k} = t2.{k}' for k in group_keys])}
            AND t1.{date_field} = t2.max_date
        """
        
        try:
            result = self.db.execute_sync_query(query)
            return result
        except Exception as e:
            logger.error(f"加载最新记录失败 [{self.table_name}]: {e}")
            logger.error(f"查询 SQL: {query}")
            import traceback
            logger.error(f"异常堆栈: {traceback.format_exc()}")
            return []
    
    def load_first_records(self, date_field: str = None, primary_keys: List[str] = None) -> List[Dict[str, Any]]:
        """
        加载每个主键分组中最早日期的记录
        
        常用于：
        - 获取每只股票的第一根K线日期
        - 需要全局“起点记录”的场景
        
        Args:
            date_field: 日期字段名（如果为None，从schema中自动获取）
            primary_keys: 主键列表（如果为None，从schema中自动获取）
            
        Returns:
            List[Dict]: 最早记录列表
        """
        if date_field is None:
            date_field = self._get_date_field_from_schema()
        
        if primary_keys is None:
            primary_keys = self._get_primary_keys_from_schema()
        
        # 过滤掉日期字段（日期字段不用于分组）
        group_keys = [k for k in primary_keys if k != date_field]
        
        if not group_keys:
            # 没有分组键，返回最早的一条记录
            first_record = self.load_one("1=1", order_by=f"{date_field} ASC")
            return [first_record] if first_record else []
        
        group_keys_str = ', '.join(group_keys)
        query = f"""
            SELECT t1.*
            FROM {self.table_name} t1
            INNER JOIN (
                SELECT {group_keys_str}, MIN({date_field}) as min_date
                FROM {self.table_name}
                GROUP BY {group_keys_str}
            ) t2
            ON {' AND '.join([f't1.{k} = t2.{k}' for k in group_keys])}
            AND t1.{date_field} = t2.min_date
        """
        
        try:
            return self.db.execute_sync_query(query)
        except Exception as e:
            logger.error(f"加载最早记录失败 [{self.table_name}]: {e}")
            return []
    
    def _get_date_field_from_schema(self) -> str:
        """
        从schema中获取日期字段名
        
        Returns:
            str: 日期字段名
            
        Raises:
            ValueError: 如果未找到日期字段
        """
        if not hasattr(self, 'schema') or not self.schema:
            raise ValueError(f"表 {self.table_name} 没有schema信息")
        
        # 常见的日期字段名
        date_field_candidates = ['date', 'trade_date', 'quarter', 'end_date', 'ann_date']
        
        # 从fields中查找
        fields = self.schema.get('fields', [])
        for field in fields:
            if field['name'] in date_field_candidates:
                return field['name']
        
        raise ValueError(
            f"表 {self.table_name} 的schema中未找到日期字段。"
            f"请在schema中添加以下任一字段: {', '.join(date_field_candidates)}"
        )
    
    def _get_primary_keys_from_schema(self) -> List[str]:
        """
        从schema中获取主键列表
        
        Returns:
            List[str]: 主键列表
            
        Raises:
            ValueError: 如果schema不存在或主键配置不正确
        """
        if not hasattr(self, 'schema') or not self.schema:
            raise ValueError(f"表 {self.table_name} 没有schema信息")
        
        primary_key = self.schema.get('primaryKey')
        
        if not primary_key:
            raise ValueError(f"表 {self.table_name} 的schema中未配置主键")
        
        if isinstance(primary_key, str):
            return [primary_key]
        elif isinstance(primary_key, list):
            return primary_key
        else:
            raise ValueError(f"表 {self.table_name} 的主键格式不正确: {primary_key}，应为字符串或列表")

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

    def _get_insert_batch_size(self) -> int:
        """从配置中获取 insert_batch_size"""
        batch_config = self.db.config.get('batch_write', {})
        advanced_config = batch_config.get('_advanced', {})
        return advanced_config.get('insert_batch_size', 5000)
    
    def insert(self, data_list: List[Dict[str, Any]], unique_keys: List[str] = None, use_batch: bool = False) -> int:
        """
        插入数据
        
        Args:
            data_list: 数据列表
            unique_keys: 唯一键列表（可选）。如果提供，将使用 INSERT ... ON CONFLICT DO NOTHING
                        如果不提供，使用纯 INSERT（可能重复插入）
            use_batch: 是否使用批量插入模式（默认 False）
                      - False: 使用批量写入队列（异步，适合并发场景）
                      - True: 使用显式批量插入（同步，适合单线程或需要立即返回的场景）
        
        Returns:
            插入的记录数
        """
        if not data_list:
            return 0
        
        if use_batch:
            # 使用显式批量插入
            return self.batch_insert(data_list, unique_keys)
        else:
            # 使用批量写入队列（默认）
            try:
                # 定义回调函数（可选，仅用于日志）
                def write_callback(table_name, count):
                    if getattr(self.db, 'is_verbose', False):
                        logger.debug(f"Insert completed for {table_name}: {count} records")
                
                # 如果提供了 unique_keys，使用 queue_write（会使用 INSERT ... ON CONFLICT）
                # 如果没有提供 unique_keys，也使用 queue_write，但需要特殊处理（纯 INSERT）
                if hasattr(self.db, 'queue_write'):
                    # 如果没有 unique_keys，使用空列表（queue_write 会处理为纯 INSERT）
                    keys = unique_keys if unique_keys else []
                    self.db.queue_write(self.table_name, data_list, keys, write_callback)
                    return len(data_list)
                
                # 兜底方案：直接执行批量插入
                return self.batch_insert(data_list, unique_keys)
            except Exception as e:
                logger.error(f"Failed to insert data into {self.table_name}: {e}")
                return 0
    
    def batch_insert(self, data_list: List[Dict[str, Any]], unique_keys: List[str] = None) -> int:
        """
        显式批量插入数据（同步执行）
        
        使用批量 VALUES 语法，自动分批处理，避免 SQL 语句过长。
        适合单线程场景或需要立即返回结果的场景。
        
        Args:
            data_list: 数据列表
            unique_keys: 唯一键列表（可选）。如果提供，将使用 INSERT ... ON CONFLICT DO NOTHING
                        如果不提供，使用纯 INSERT（可能重复插入）
        
        Returns:
            插入的记录数
        """
        if not data_list:
            return 0
        
        try:
            # 准备数据
            if unique_keys:
                columns, values, update_clause = DBHelper.to_upsert_params(data_list, unique_keys)
            else:
                columns, _ = DBHelper.to_columns_and_values(data_list)
                values = [tuple(data[col] for col in columns) for data in data_list]
                update_clause = None
            
            if not columns:
                return 0
            
            # 获取批量大小配置
            batch_size = self._get_insert_batch_size()
            
            # 使用 BatchInsertHelper 执行批量插入
            with self.db.get_sync_cursor() as cursor:
                return BatchOperation.execute_batch_insert(
                    executor=cursor,
                    table_name=self.table_name,
                    columns=columns,
                    values=values,
                    batch_size=batch_size,
                    unique_keys=unique_keys if unique_keys else None,
                    update_clause=update_clause
                )
        except Exception as e:
            logger.error(f"Failed to batch insert data into {self.table_name}: {e}")
            return 0
    

    def insert_one(self, data: Dict[str, Any]) -> int:
        """插入单条数据"""
        return self.insert([data])

    def update(self, data: Dict[str, Any], condition: str, params: tuple = ()) -> int:
        """更新数据（别名方法）"""
        try:
            # 使用 ? 占位符（execute_sync_query 会自动转换 %s -> ?）
            set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
            query = f"UPDATE {self.table_name} SET {set_clause} WHERE {condition}"
            
            # 转换 condition 中的 %s 为 ?
            query = query.replace("%s", "?")
            
            with self.db.get_sync_cursor() as cursor:
                cursor.execute(query, tuple(data.values()) + params)
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Failed to update data in {self.table_name}: {e}")
            return 0


    # ***********************************
    #        data upsert operations
    # ***********************************
    def replace(self, data_list: List[Dict[str, Any]], unique_keys: List[str], use_batch: bool = False) -> int:
        """
        插入或更新数据（Upsert）
        
        Args:
            data_list: 数据列表
            unique_keys: 唯一键列表（用于判断是否已存在）
            use_batch: 是否使用批量插入模式（默认 False）
                      - False: 使用批量写入队列（异步，适合并发场景）
                      - True: 使用显式批量插入（同步，适合单线程或需要立即返回的场景）
        
        Returns:
            插入或更新的记录数
        """
        if not data_list:
            return 0
        
        if use_batch:
            # 使用显式批量插入
            return self.batch_replace(data_list, unique_keys)
        else:
            # 使用批量写入队列（默认）
            try:
                # 定义回调函数（可选，仅用于日志）
                def write_callback(table_name, count):
                    if getattr(self.db, 'is_verbose', False):
                        logger.info(f"Upsert completed for {table_name}: {count} records")
                
                # 交给 DatabaseManager 统一处理（内部使用 INSERT ... ON CONFLICT DO UPDATE）
                if hasattr(self.db, 'queue_write'):
                    self.db.queue_write(self.table_name, data_list, unique_keys, write_callback)
                    return len(data_list)
                
                # 兜底方案：直接执行批量插入
                return self.batch_replace(data_list, unique_keys)
            except Exception as e:
                logger.error(f"Failed to upsert data in {self.table_name}: {e}")
                return 0
    
    def batch_replace(self, data_list: List[Dict[str, Any]], unique_keys: List[str]) -> int:
        """
        显式批量插入或更新数据（同步执行）
        
        使用 INSERT ... ON CONFLICT DO UPDATE 语法，自动分批处理，避免 SQL 语句过长。
        适合单线程场景或需要立即返回结果的场景。
        
        Args:
            data_list: 数据列表
            unique_keys: 唯一键列表（用于判断是否已存在）
        
        Returns:
            插入或更新的记录数
        """
        if not data_list:
            return 0
        
        try:
            # 准备数据
            columns, values, update_clause = DBHelper.to_upsert_params(data_list, unique_keys)
            
            if not columns:
                return 0
            
            # 获取批量大小配置
            batch_size = self._get_insert_batch_size()
            
            # 使用 BatchInsertHelper 执行批量插入
            with self.db.get_sync_cursor() as cursor:
                return BatchOperation.execute_batch_insert(
                    executor=cursor,
                    table_name=self.table_name,
                    columns=columns,
                    values=values,
                    batch_size=batch_size,
                    unique_keys=unique_keys,
                    update_clause=update_clause
                )
        except Exception as e:
            logger.error(f"Failed to batch upsert data in {self.table_name}: {e}")
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
            # 转换占位符 %s -> ?
            query = query.replace("%s", "?")
            
            with self.db.get_sync_cursor() as cursor:
                cursor.execute(query, params)
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
