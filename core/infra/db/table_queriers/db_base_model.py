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
from core.infra.db.table_queriers.services.batch_operation import BatchOperation


class DbBaseModel:
    """
    通用表操作模型基类（顶层类，不继承 Helper）

    所有基础表的 Model 类都继承自此类，提供单表的 CRUD 操作。
    """
    
    def __init__(self, table_name: str, db=None):
        """
        初始化表模型

        Args:
            table_name: 表名
            db: DatabaseManager 实例（可选，测试时传入；默认使用 get_default）
        """
        from core.infra.db import DatabaseManager
        self.db = db if db is not None else DatabaseManager.get_default(auto_init=True)
        self.table_name = table_name
        self.schema = self.load_schema()
        self.verbose = False
        self.is_base_table = False

    # ***********************************
    #        table operations
    # ***********************************
    
    def load_schema(self) -> dict:
        """
        加载表的 schema。由基类统一实现：通过 SchemaManager 按 self.table_name
        从 core/tables 下各表目录的 schema.py 加载（按 schema["name"] 索引）；
        子类无需覆盖，只需在 __init__ 中传入正确的 table_name 即可。
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

    def is_table_empty(self) -> bool:
        """检查表是否为空"""
        return self.count() == 0

    def _validate_column_name(self, name: str) -> None:
        """校验列名，防止 SQL 注入（仅允许字母、数字、下划线）"""
        import re
        if not name or not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name):
            raise ValueError(f"无效的列名: {name!r}，仅允许字母、数字、下划线")

    def _validate_column_type(self, column_type: str) -> None:
        """校验列类型，防止 SQL 注入（允许常见类型如 VARCHAR(255)、DECIMAL(10,2)）"""
        import re
        if not column_type or not re.match(r'^[a-zA-Z0-9_(),\s]+$', column_type.strip()):
            raise ValueError(f"无效的列类型: {column_type!r}")

    def add_column(self, column_name: str, column_type: str) -> None:
        """
        添加列

        Args:
            column_name: 列名
            column_type: 列类型（如 VARCHAR(255)、INTEGER、TEXT、DECIMAL(10,2)）
        """
        self._validate_column_name(column_name)
        self._validate_column_type(column_type)
        sql = f"ALTER TABLE {self.table_name} ADD COLUMN {column_name} {column_type.strip()}"
        with self.db.get_sync_cursor() as cursor:
            cursor.execute(sql)
        if self.db.is_verbose:
            logger.info(f"表 {self.table_name} 已添加列: {column_name}")

    def drop_column(self, column_name: str) -> None:
        """
        删除列

        Args:
            column_name: 列名
        """
        self._validate_column_name(column_name)
        sql = f"ALTER TABLE {self.table_name} DROP COLUMN {column_name}"
        with self.db.get_sync_cursor() as cursor:
            cursor.execute(sql)
        if self.db.is_verbose:
            logger.info(f"表 {self.table_name} 已删除列: {column_name}")

    def rename_column(self, old_column_name: str, new_column_name: str) -> None:
        """
        重命名列

        Args:
            old_column_name: 原列名
            new_column_name: 新列名
        """
        self._validate_column_name(old_column_name)
        self._validate_column_name(new_column_name)
        sql = f"ALTER TABLE {self.table_name} RENAME COLUMN {old_column_name} TO {new_column_name}"
        with self.db.get_sync_cursor() as cursor:
            cursor.execute(sql)
        if self.db.is_verbose:
            logger.info(f"表 {self.table_name} 已将列 {old_column_name} 重命名为 {new_column_name}")

    def modify_column(self, column_name: str, column_type: str) -> None:
        """
        修改列类型

        Args:
            column_name: 列名
            column_type: 新的列类型

        Raises:
            NotImplementedError: SQLite 不支持 ALTER COLUMN，需重建表
        """
        self._validate_column_name(column_name)
        self._validate_column_type(column_type)
        database_type = self.db.config.get('database_type', 'postgresql')
        if database_type == 'sqlite':
            raise NotImplementedError(
                "SQLite 不支持修改列类型。请使用 execute_raw_update 手动重建表，"
                "或迁移到 PostgreSQL/MySQL。"
            )
        if database_type == 'postgresql':
            sql = f"ALTER TABLE {self.table_name} ALTER COLUMN {column_name} TYPE {column_type.strip()}"
        else:
            sql = f"ALTER TABLE {self.table_name} MODIFY COLUMN `{column_name}` {column_type.strip()}"
        with self.db.get_sync_cursor() as cursor:
            cursor.execute(sql)
        if self.db.is_verbose:
            logger.info(f"表 {self.table_name} 已将列 {column_name} 类型修改为 {column_type}")

    def get_primary_keys(self) -> List[str]:
        """从 schema 中获取主键列表"""
        if not hasattr(self, 'schema') or not self.schema:
            raise ValueError(f"表 {self.table_name} 没有 schema 信息")
        primary_key = self.schema.get('primaryKey')
        if not primary_key:
            raise ValueError(f"表 {self.table_name} 的 schema 中未配置主键")
        if isinstance(primary_key, str):
            return [primary_key]
        if isinstance(primary_key, list):
            return primary_key
        raise ValueError(f"表 {self.table_name} 的主键格式不正确: {primary_key}")


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
        
        # 获取当前页数据（直接使用 load）
        data = self.load(
            condition="1=1",
            params=(),
            order_by=order_by,
            limit=page_size,
            offset=offset,
        )
        
        return {
            'data': data,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size
        }

    def load_first(self, date_field: str) -> Optional[Dict[str, Any]]:
        """
        加载最早一条记录
        
        Args:
            date_field: 用于排序的日期字段名（例如 'date'、'trade_date' 等）
        """
        return self.load_one("1=1", order_by=f"{date_field} ASC")

    def load_firsts(self, date_field: str, group_fields: List[str]) -> List[Dict[str, Any]]:
        """
        加载每个分组中最早日期的记录

        Args:
            date_field: 日期字段名（用于取 MIN）
            group_fields: 分组字段列表（GROUP BY 的字段）
        """
        if not group_fields:
            raise ValueError("group_fields 不能为空，需传入至少一个分组字段")
        group_fields_str = ', '.join(group_fields)
        query = f"""
            SELECT t1.*
            FROM {self.table_name} t1
            INNER JOIN (
                SELECT {group_fields_str}, MIN({date_field}) as min_date
                FROM {self.table_name}
                GROUP BY {group_fields_str}
            ) t2
            ON {' AND '.join([f't1.{f} = t2.{f}' for f in group_fields])}
            AND t1.{date_field} = t2.min_date
        """
        try:
            return self.db.execute_sync_query(query)
        except Exception as e:
            logger.error(f"加载最早记录失败 [{self.table_name}]: {e}")
            return []


    def load_latest(self, date_field: str) -> Optional[Dict[str, Any]]:
        """
        加载最新一条记录

        Args:
            date_field: 用于排序的日期字段名（例如 'date'、'trade_date' 等）
        """
        return self.load_one("1=1", order_by=f"{date_field} DESC")

    def load_latests(self, date_field: str, group_fields: List[str]) -> List[Dict[str, Any]]:
        """
        加载每个分组中最新日期的记录

        Args:
            date_field: 日期字段名（用于取 MAX）
            group_fields: 分组字段列表（GROUP BY 的字段）
        """
        if not group_fields:
            raise ValueError("group_fields 不能为空，需传入至少一个分组字段")
        group_fields_str = ', '.join(group_fields)
        query = f"""
            SELECT t1.*
            FROM {self.table_name} t1
            INNER JOIN (
                SELECT {group_fields_str}, MAX({date_field}) as max_date
                FROM {self.table_name}
                GROUP BY {group_fields_str}
            ) t2
            ON {' AND '.join([f't1.{f} = t2.{f}' for f in group_fields])}
            AND t1.{date_field} = t2.max_date
        """
        try:
            return self.db.execute_sync_query(query)
        except Exception as e:
            logger.error(f"加载最新记录失败 [{self.table_name}]: {e}")
            return []

    def load_latest_date(self, date_field: str) -> Optional[str]:
        latest_record = self.load_latest(date_field)
        return latest_record[date_field] if latest_record else None

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


    def delete_many(self, data_list: List[Dict[str, Any]]) -> int:
        """删除多条数据"""
        pass

    def delete_all(self) -> int:
        """删除所有数据"""
        return self.clear_table()


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
        核心插入 API（同步）。
        
        - 支持单条或多条（由 data_list 长度决定）
        - 默认行为：**同步写入**，调用返回时数据已落库
        - 内部统一通过批次实现（_batch_insert）
        """
        if not data_list:
            return 0
        # 统一走批次实现
        return self.batch_insert(data_list, unique_keys)

    def insert_async(self, data_list: List[Dict[str, Any]], unique_keys: List[str] = None) -> int:
        """
        核心插入 API（异步，使用批量写入队列）。
        
        - 适合高并发、大批量写入场景
        - 调用返回时数据**可能尚未真正写入数据库**，由后台队列按 batch_size/flush_interval 决定实际落库时间
        """
        if not data_list:
            return 0

        try:
            def write_callback(table_name, count):
                if getattr(self.db, "is_verbose", False):
                    logger.debug(f"Insert completed for {table_name}: {count} records")

            if hasattr(self.db, "queue_write"):
                keys = unique_keys if unique_keys else []
                self.db.queue_write(self.table_name, data_list, keys, write_callback)
                return len(data_list)

            # 无队列时退化为同步批次插入
            return self.batch_insert(data_list, unique_keys)
        except Exception as e:
            logger.error(f"Failed to insert data into {self.table_name} (async): {e}")
            return 0
    
    def batch_insert(self, data_list: List[Dict[str, Any]], unique_keys: List[str] = None) -> int:
        """
        显式批量插入数据（同步执行，内部批次实现）
        
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
        """插入单条数据（wrapper，内部调用 insert）"""
        return self.insert([data])

    def insert_many(self, rows: List[Dict[str, Any]], unique_keys: List[str] = None) -> int:
        """
        批量插入（同步）。

        建议在业务层统一使用本方法处理多行插入：
        - 内部使用批次逻辑（batch_insert），调用返回时数据已落库。
        - unique_keys 不为空时，将使用 INSERT ... ON CONFLICT DO NOTHING 语义。
        """
        return self.insert(rows, unique_keys)

    def insert_many_async(self, rows: List[Dict[str, Any]], unique_keys: List[str] = None) -> int:
        """
        批量插入（异步，使用写入队列）。

        - 适合高并发、大批量写入场景。
        - 返回值为入队行数，实际落库由后台线程按 batch_size/flush_interval 决定。
        - 新代码建议优先使用本方法，而不是直接调用 insert_async。
        """
        return self.insert_async(rows, unique_keys)



    # ***********************************
    #        data upsert operations（统一使用 upsert 命名）
    # ***********************************

    def upsert(self, rows: List[Dict[str, Any]], unique_keys: List[str]) -> int:
        """
        核心 Upsert API（同步，多条）。
        """
        return self._batch_upsert(rows, unique_keys)

    def upsert_async(self, rows: List[Dict[str, Any]], unique_keys: List[str]) -> int:
        """
        核心 Upsert API（异步，多条）。
        """
        if not rows:
            return 0
        try:
            def write_callback(table_name, count):
                if getattr(self.db, "is_verbose", False):
                    logger.info(f"Upsert completed for {table_name}: {count} records")
            if hasattr(self.db, "queue_write"):
                self.db.queue_write(self.table_name, rows, unique_keys, write_callback)
                return len(rows)
            return self._batch_upsert(rows, unique_keys)
        except Exception as e:
            logger.error(f"Failed to upsert data in {self.table_name} (async): {e}")
            return 0

    def _batch_upsert(self, rows: List[Dict[str, Any]], unique_keys: List[str]) -> int:
        """
        内部实现：按批次同步执行 upsert（INSERT ... ON CONFLICT DO UPDATE）。
        不对外暴露，由 upsert_one / upsert_many 调用。
        """
        if not rows:
            return 0
        try:
            columns, values, update_clause = DBHelper.to_upsert_params(rows, unique_keys)
            if not columns:
                return 0
            batch_size = self._get_insert_batch_size()
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
            logger.error(f"Failed to upsert data in {self.table_name}: {e}")
            return 0

    def upsert_one(self, row: Dict[str, Any], unique_keys: List[str]) -> int:
        """
        Upsert 单条数据（同步，wrapper）。
        """
        return self.upsert([row], unique_keys)

    def upsert_many(self, rows: List[Dict[str, Any]], unique_keys: List[str]) -> int:
        """
        Upsert 多条数据（同步，wrapper）。
        """
        return self.upsert(rows, unique_keys)

    def upsert_many_async(self, rows: List[Dict[str, Any]], unique_keys: List[str]) -> int:
        """
        Upsert 多条数据（异步，wrapper）。
        """
        return self.upsert_async(rows, unique_keys)

    
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
