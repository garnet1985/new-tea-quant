"""
DbBaseModel - 数据库表操作的通用基类

这是一个纯粹的工具类，封装了常见的数据库表操作，提供：
- 基础 CRUD（增删改查）
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
    from app.core.infra.db import DbBaseModel
    from app.core.infra.db import DatabaseManager
    
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

from .db_config_manager import DB_CONFIG


class DBService:
    """数据库操作辅助工具类（纯静态方法）"""
    
    @staticmethod
    def to_columns_and_values(data_list: List[Dict[str, Any]]) -> tuple:
        """
        将数据列表转换为插入语句的列名和占位符
        
        Args:
            data_list: 数据字典列表
            
        Returns:
            (columns, placeholders): 列名列表和占位符字符串
            
        Example:
            columns, placeholders = DBService.to_columns_and_values([
                {'id': '001', 'name': 'test'}
            ])
            # columns = ['id', 'name']
            # placeholders = '%s, %s'
        """
        if not data_list:
            return [], ""
        
        columns = list(data_list[0].keys())
        placeholders = ', '.join(['%s'] * len(columns))
        return columns, placeholders
    
    @staticmethod
    def to_upsert_params(data_list: List[Dict[str, Any]], unique_keys: List[str]) -> tuple:
        """
        将数据列表转换为 upsert 语句的参数
        
        Args:
            data_list: 数据字典列表
            unique_keys: 唯一键列表（用于判断是否已存在）
            
        Returns:
            (columns, values, update_clause): 列名、值列表、UPDATE 子句
            
        Example:
            columns, values, update_clause = DBService.to_upsert_params(
                [{'id': '001', 'name': 'test', 'price': 10.0}],
                unique_keys=['id']
            )
            # columns = ['id', 'name', 'price']
            # values = [('001', 'test', 10.0)]
            # update_clause = 'name = VALUES(name), price = VALUES(price)'
        """
        if not data_list:
            return [], [], ""
        
        columns = list(data_list[0].keys())
        
        # 检查 unique_keys 是否都在数据列中存在
        missing_keys = [k for k in unique_keys if k not in columns]
        if missing_keys:
            raise ValueError(f"主键字段在数据中缺失: {missing_keys}")
        
        # 为字段名添加反引号（处理 MySQL 保留字，如 'key'）
        escaped_columns = [f"`{col}`" for col in columns]
        
        # 构建 update 子句（排除 unique_keys 中的字段）
        update_fields = [k for k in columns if k not in unique_keys]
        update_clause = ', '.join([f"`{k}` = VALUES(`{k}`)" for k in update_fields])
        
        # 构建值列表
        values = [tuple(data[col] for col in columns) for data in data_list]
        
        return escaped_columns, values, update_clause
    
    @staticmethod
    def clean_nan_value(value: Any, default: Any = None) -> Any:
        """
        清理单个值中的 NaN，转换为 None 或默认值
        
        处理各种类型的 NaN：
        - numpy.nan (float)
        - pandas.NA
        - pandas.NaT
        - None
        
        Args:
            value: 原始值（可能是 NaN）
            default: 默认值（当值为 NaN 时返回，默认为 None）
            
        Returns:
            清理后的值（NaN -> default，其他值保持原样）
            
        Example:
            DBService.clean_nan_value(float('nan'))  # None
            DBService.clean_nan_value(None)  # None
            DBService.clean_nan_value(123.45)  # 123.45
            DBService.clean_nan_value(float('nan'), default=0.0)  # 0.0
        """
        if value is None:
            return default
        
        # 检查是否是 float 类型的 NaN
        try:
            if isinstance(value, float) and math.isnan(value):
                return default
        except (TypeError, ValueError):
            pass
        
        # 检查是否是 pandas 的 NA 类型
        try:
            import pandas as pd
            if pd.isna(value):
                return default
        except (ImportError, AttributeError, TypeError):
            pass
        
        return value
    
    @staticmethod
    def clean_nan_in_dict(data: Dict[str, Any], default: Any = None) -> Dict[str, Any]:
        """
        清理字典中所有值的 NaN
        
        Args:
            data: 原始字典
            default: 默认值（当值为 NaN 时替换为，默认为 None）
            
        Returns:
            清理后的字典
            
        Example:
            data = {'a': 1.0, 'b': float('nan'), 'c': None}
            cleaned = DBService.clean_nan_in_dict(data, default=0.0)
            # {'a': 1.0, 'b': 0.0, 'c': 0.0}
        """
        if not isinstance(data, dict):
            return data
        
        cleaned = {}
        for key, value in data.items():
            cleaned[key] = DBService.clean_nan_value(value, default=default)
        return cleaned
    
    @staticmethod
    def clean_nan_in_list(data_list: List[Dict[str, Any]], default: Any = None) -> List[Dict[str, Any]]:
        """
        清理列表中所有字典的 NaN 值
        
        Args:
            data_list: 字典列表
            default: 默认值（当值为 NaN 时替换为，默认为 None）
            
        Returns:
            清理后的字典列表
            
        Example:
            data_list = [
                {'id': '001', 'value': 1.0},
                {'id': '002', 'value': float('nan')}
            ]
            cleaned = DBService.clean_nan_in_list(data_list, default=0.0)
            # [{'id': '001', 'value': 1.0}, {'id': '002', 'value': 0.0}]
        """
        if not isinstance(data_list, list):
            return data_list
        
        return [DBService.clean_nan_in_dict(item, default=default) for item in data_list]


class DbBaseModel:
    """
    通用表操作模型基类
    
    ⚠️  DEPRECATED: 本类计划废弃，请使用 DataManager 替代
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
        from .db_manager import DatabaseManager
        
        # 自动获取或使用传入的 db
        self.db = db if db is not None else DatabaseManager.get_default()
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
        """
        # 尝试从 base_tables 加载
        # 从 app/core/infra/db 向上找到项目根，再定位到 app/core/modules/data_manager/base_tables
        current_dir = os.path.dirname(__file__)  # app/core/infra/db
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))  # 项目根
        base_schema_path = os.path.join(
            project_root,
            'app', 'core', 'modules', 'data_manager', 'base_tables', 
            self.table_name, 'schema.json'
        )
        
        if os.path.exists(base_schema_path):
            try:
                with open(base_schema_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load schema from {base_schema_path}: {e}")
        
        # 如果不存在，可能是策略自定义表（暂不处理）
        logger.warning(f"Schema not found for table {self.table_name}")
        return None


    def create_table(self, custom_table_name: str = None) -> None:
        if not self.schema:
            logger.error(f"Failed create table: {self.table_name}, because schema is not found")
            return

        # 使用 DbSchemaManager 生成 SQL
        from .db_schema_manager import DbSchemaManager
        schema_manager = DbSchemaManager(charset=DB_CONFIG['base']['charset'])
        
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
    
    def load_latest_date(self, date_field: str = None) -> Optional[str]:
        """
        加载表中最新的日期
        
        Args:
            date_field: 日期字段名（如果为None，从schema中自动获取）
            
        Returns:
            Optional[str]: 最新日期，如果表为空返回None
            
        Raises:
            ValueError: 如果日期字段未找到
        """
        if date_field is None:
            # 从schema中查找日期字段（可能抛出异常）
            date_field = self._get_date_field_from_schema()
        
        # 查询最新日期
        latest_record = self.load_one("1=1", order_by=f"{date_field} DESC")
        return latest_record.get(date_field) if latest_record else None
    
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
            return self.db.execute_sync_query(query)
        except Exception as e:
            logger.error(f"加载最新记录失败 [{self.table_name}]: {e}")
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
                def write_callback(table_name, count):
                    if self.db.is_verbose:
                        logger.info(f"Async write completed for {table_name}: {count} records")
                
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
    #        DataFrame Support Methods
    # ***********************************
    
    def load_many_df(self, condition: str = "1=1", params: tuple = (), 
                     limit: int = None, order_by: str = None, offset: int = None):
        """
        加载多条记录，返回DataFrame
        
        适用场景：
        - 需要数据分析（merge、groupby、rolling等）
        - 需要批量计算（向量化操作）
        - 需要处理时间序列
        - 需要数据清洗和转换
        
        Args:
            condition: 查询条件
            params: 查询参数
            limit: 返回记录数限制
            order_by: 排序字段
            offset: 偏移量
            
        Returns:
            pd.DataFrame: 查询结果（如果无数据返回空DataFrame）
            
        示例：
            # 加载K线数据
            df = table.load_many_df(
                condition="id=%s AND term=%s",
                params=('000001.SZ', 'daily'),
                order_by='date'
            )
            
            # 计算移动平均
            df['ma5'] = df['close'].rolling(5).mean()
            
            # 分组聚合
            stats = df.groupby('id')['close'].agg(['mean', 'std'])
        """
        try:
            import pandas as pd
        except ImportError:
            logger.error("pandas未安装，无法使用load_many_df方法")
            return None
        
        records = self.load_many(condition, params, limit, order_by, offset)
        return pd.DataFrame(records) if records else pd.DataFrame()
    
    def load_all_df(self, condition: str = "1=1", params: tuple = (), order_by: str = None):
        """
        加载所有记录，返回DataFrame
        
        适用场景：需要对整表进行分析时使用
        
        Returns:
            pd.DataFrame: 查询结果
        """
        try:
            import pandas as pd
        except ImportError:
            logger.error("pandas未安装，无法使用load_all_df方法")
            return None
        
        records = self.load_all(condition, params, order_by)
        return pd.DataFrame(records) if records else pd.DataFrame()
    
    def insert_df(self, df) -> int:
        """
        插入DataFrame数据
        
        说明：
        - 内部转换为list后调用insert方法
        - 保留所有自定义逻辑（批量插入、错误处理等）
        - 支持大数据量的批量插入
        
        Args:
            df: pandas DataFrame，列名应与数据库字段名一致
            
        Returns:
            int: 插入的记录数
            
        示例：
            import pandas as pd
            
            df = pd.DataFrame({
                'id': ['000001.SZ', '000002.SZ'],
                'name': ['平安银行', '万科A'],
                'date': ['20250930', '20250930']
            })
            
            count = table.insert_df(df)
        """
        try:
            import pandas as pd
        except ImportError:
            logger.error("pandas未安装，无法使用insert_df方法")
            return 0
        
        if not isinstance(df, pd.DataFrame):
            logger.error(f"insert_df expects pandas DataFrame, got {type(df)}")
            return 0
        
        if df.empty:
            logger.debug("DataFrame is empty, skipping insert")
            return 0
        
        # 转换为dict列表后调用原insert方法
        data_list = df.to_dict('records')
        return self.insert(data_list)
    
    def replace_df(self, df, unique_keys: List[str]) -> int:
        """
        Upsert DataFrame数据（基于主键更新或插入）
        
        说明：
        - 内部转换为list后调用replace方法
        - 保留所有自定义逻辑（异步队列、线程安全、错误重试等）
        - 支持大数据量的批量upsert
        
        Args:
            df: pandas DataFrame，列名应与数据库字段名一致
            unique_keys: 用于判断记录唯一性的字段列表（通常是主键）
            
        Returns:
            int: 影响的记录数
            
        示例：
            # 更新K线数据（如果存在则更新，不存在则插入）
            df = pd.DataFrame({
                'id': ['000001.SZ', '000001.SZ'],
                'term': ['daily', 'daily'],
                'date': ['20250929', '20250930'],
                'close': [11.34, 11.40]
            })
            
            count = table.replace_df(df, unique_keys=['id', 'term', 'date'])
        """
        try:
            import pandas as pd
        except ImportError:
            logger.error("pandas未安装，无法使用replace_df方法")
            return 0
        
        if not isinstance(df, pd.DataFrame):
            logger.error(f"replace_df expects pandas DataFrame, got {type(df)}")
            return 0
        
        if df.empty:
            logger.debug("DataFrame is empty, skipping replace")
            return 0
        
        # 转换为dict列表后调用原replace方法
        data_list = df.to_dict('records')
        return self.replace(data_list, unique_keys)
    
    
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
