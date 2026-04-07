"""
DBHelpers - 数据库操作辅助工具

提供纯静态方法，用于数据转换和处理、游标包装等。

方言相关（MySQL / PostgreSQL / SQLite 标识符引用等）请统一通过 :class:`DBHelper` 的
``quote_identifier*`` 方法处理；userspace 与业务代码不要直接依赖底层 ``sql_identifiers`` 模块。
"""
import math
from typing import Dict, List, Any, Optional

from core.infra.db.helpers.sql_identifiers import quote_ddl_identifier as _quote_ddl_identifier_impl
from core.infra.db.table_queriers.adapters.base_adapter import BaseDatabaseAdapter


class DBHelper:
    """数据库操作辅助工具类（纯静态方法）"""
    
    @staticmethod
    def parse_database_config(config: Dict) -> Dict:
        """
        解析和验证数据库配置
        
        职责：
        1. 验证配置的完整性和有效性
        2. 补足缺失的默认配置
        
        Args:
            config: 配置字典（来自 ConfigManager.load_database_config()）
            
        Returns:
            解析和验证后的配置字典
            
        Raises:
            ValueError: 配置格式错误或缺少必需字段
        """
        # 1. 验证 database_type
        database_type = config.get('database_type')
        if not database_type:
            raise ValueError("配置中缺少 'database_type' 字段")
        
        database_type = database_type.lower()
        valid_types = ['postgresql', 'mysql', 'sqlite']
        if database_type not in valid_types:
            raise ValueError(
                f"不支持的数据库类型: {database_type}，"
                f"支持的类型: {', '.join(valid_types)}"
            )
        
        # 2. 验证对应的数据库配置是否存在
        db_config = config.get(database_type)
        if not db_config:
            raise ValueError(
                f"配置中缺少 '{database_type}' 数据库配置，"
                f"请确保配置中包含 '{database_type}' 字段"
            )
        
        # 3. 验证数据库配置的必需字段
        if database_type == 'sqlite':
            if 'db_path' not in db_config:
                raise ValueError("SQLite 配置中缺少 'db_path' 字段")
        elif database_type in ['postgresql', 'mysql']:
            required_fields = ['host', 'port', 'database', 'user', 'password']
            missing_fields = [f for f in required_fields if f not in db_config]
            if missing_fields:
                raise ValueError(
                    f"{database_type.upper()} 配置中缺少必需字段: {', '.join(missing_fields)}"
                )

            # PostgreSQL: 补全 pgsql_schema，默认 public
            if database_type == 'postgresql':
                db_config['pgsql_schema'] = db_config.get('default_pgsql_schema')
        
        # 4. 补足 batch_write 默认配置
        if 'batch_write' not in config:
            config['batch_write'] = {
                'enable': True,
                'batch_size': 1000,
                'flush_interval': 5.0
            }
        else:
            # 确保 batch_write 有必需的字段
            batch_write = config['batch_write']
            if 'enable' not in batch_write:
                batch_write['enable'] = True
            if 'batch_size' not in batch_write:
                batch_write['batch_size'] = 1000
            if 'flush_interval' not in batch_write:
                batch_write['flush_interval'] = 5.0
        
        # 5. 确保 database_type 使用小写
        config['database_type'] = database_type
        
        return config
    
    @staticmethod
    def to_columns_and_values(data_list: List[Dict[str, Any]]) -> tuple:
        """
        将数据列表转换为插入语句的列名和占位符
        
        Args:
            data_list: 数据字典列表
            
        Returns:
            (columns, placeholders): 列名列表和占位符字符串
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
        """
        if not data_list:
            return [], [], ""
        
        # 使用原始列名
        columns = list(data_list[0].keys())
        
        # 检查 unique_keys 是否都在数据列中存在
        missing_keys = [k for k in unique_keys if k not in columns]
        if missing_keys:
            raise ValueError(f"主键字段在数据中缺失: {missing_keys}")
        
        # 构建 ON CONFLICT ... DO UPDATE 子句（排除 unique_keys 中的字段）
        update_fields = [k for k in columns if k not in unique_keys]
        update_clause = ', '.join([f"{k} = EXCLUDED.{k}" for k in update_fields]) if update_fields else ''
        
        # 构建值列表
        values = [tuple(data[col] for col in columns) for data in data_list]
        
        return columns, values, update_clause
    
    @staticmethod
    def clean_nan_value(value: Any, default: Any = None) -> Any:
        """
        清理单个值中的 NaN，转换为 None 或默认值
        
        Args:
            value: 原始值（可能是 NaN）
            default: 默认值（当值为 NaN 时返回，默认为 None）
            
        Returns:
            清理后的值（NaN -> default，其他值保持原样）
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
        """
        if not isinstance(data, dict):
            return data
        
        cleaned = {}
        for key, value in data.items():
            cleaned[key] = DBHelper.clean_nan_value(value, default=default)
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
        """
        if not isinstance(data_list, list):
            return data_list
        
        return [DBHelper.clean_nan_in_dict(item, default=default) for item in data_list]

    @staticmethod
    def normalize_database_type(config: Dict) -> str:
        """归一化为 postgresql | mysql | sqlite。"""
        raw = config.get("database_type") or "postgresql"
        t = str(raw).lower()
        if t in ("postgresql", "postgres", "pg"):
            return "postgresql"
        if t in ("mysql", "mariadb"):
            return "mysql"
        if "sqlite" in t:
            return "sqlite"
        return "postgresql"

    @staticmethod
    def quote_identifier(config: Dict, name: str) -> str:
        """
        按当前 ``database_type`` 为 SQL 标识符加引号（表名、列名、索引名等）。

        - MySQL/MariaDB：反引号
        - PostgreSQL / SQLite：双引号

        动态拼接 DDL/DML 时调用，避免 ``key`` / ``text`` / ``json`` 等与保留字冲突。
        这是业务侧应使用的**唯一入口**，不必区分方言。
        """
        dt = DBHelper.normalize_database_type(config)
        return _quote_ddl_identifier_impl(dt, name)

    @staticmethod
    def quote_identifier_for_dialect(database_type: str, name: str) -> str:
        """
        在仅有方言字符串时引用标识符（如 :class:`SchemaManager` 仅持有 ``database_type``）。

        Args:
            database_type: ``postgresql`` | ``mysql`` | ``sqlite``
        """
        return _quote_ddl_identifier_impl(database_type, name)

    @staticmethod
    def quote_identifier_list(config: Dict, names: List[str]) -> str:
        """逗号分隔的已引用列名列表，用于 ``INSERT INTO t (…)`` 等。"""
        return ", ".join(DBHelper.quote_identifier(config, n) for n in names)

    @staticmethod
    def sql_qualify_table_name(config: Dict, logical_name: str) -> str:
        """
        将逻辑表名转为 SQL 中可直接使用的表标识。

        - 已含 schema（含英文句号）时原样返回
        - PostgreSQL: {pgsql_schema}.table
        - MySQL / SQLite: 裸表名
        """
        name = logical_name.strip()
        if not name:
            raise ValueError("表名为空")
        if "." in name:
            return name
        t = DBHelper.normalize_database_type(config)
        if t == "postgresql":
            pg = config.get("postgresql") or {}
            schema = pg.get("pgsql_schema") or pg.get("default_pgsql_schema") or "public"
            return f"{schema}.{name}"
        return name


class DatabaseCursor:
    """
    通用数据库游标包装类
    
    兼容不同数据库的游标接口，统一返回字典格式的结果。
    execute() 会真正执行 SQL：写操作走 adapter.execute_write，读操作延后到 fetchall 时走 adapter.execute_query。
    """
    def __init__(self, adapter: BaseDatabaseAdapter):
        self.adapter = adapter
        self._cursor = None
        self._result = None
        self._rowcount = 0

    @staticmethod
    def _is_write_query(query: str) -> bool:
        q = query.strip().upper()
        # 写操作包括 DML 和 常见 DDL（需要立即执行并提交事务）
        return q.startswith((
            'INSERT',
            'UPDATE',
            'DELETE',
            'CREATE',
            'DROP',
            'ALTER',
            'TRUNCATE',
        ))

    def execute(self, query: str, params: Any = None):
        """执行 SQL：写操作立即执行并提交，读操作仅保存供 fetchall 使用。"""
        self._query = query
        self._params = params
        self._result = None
        self._rowcount = 0
        if self._is_write_query(query):
            self._rowcount = self.adapter.execute_write(query, params)
        return self

    def fetchall(self) -> List[Dict[str, Any]]:
        """获取所有结果，转换为字典列表（仅对读操作有效，会真正执行查询）。"""
        if not hasattr(self, '_query'):
            return []
        self._result = self.adapter.execute_query(self._query, self._params)
        return self._result

    def fetchone(self) -> Optional[Dict[str, Any]]:
        """获取一条结果"""
        results = self.fetchall()
        return results[0] if results else None

    @property
    def rowcount(self) -> int:
        """返回影响的行数（写操作来自 execute_write，读操作为 0）。"""
        if self._result is not None:
            return len(self._result)
        return getattr(self, '_rowcount', 0)

    def close(self):
        """关闭游标"""
        pass
