"""
SchemaManager - Schema 管理和表初始化

职责：
- 从 core/tables 递归加载 schema.py
- 根据 schema 生成 CREATE TABLE SQL
- 创建表和索引
- 管理策略自定义表的注册
"""
import importlib.util
import json
import logging
from typing import Dict, List, Optional, Callable
from pathlib import Path

from core.infra.project_context import PathManager, FileManager
from core.infra.db.schema_management.field import Field


logger = logging.getLogger(__name__)


class SchemaManager:
    """
    Schema 管理器
    
    职责：
    - 从 core/tables（或指定目录）递归加载 schema.py
    - 根据 schema 生成 CREATE TABLE SQL
    - 创建表和索引
    - 管理策略自定义表的注册
    """
    
    def __init__(self, tables_dir: str = None, is_verbose: bool = False, database_type: str = None):
        """
        初始化 SchemaManager
        
        Args:
            tables_dir: schema 目录（默认为 core/tables）
            is_verbose: 是否输出详细日志
            database_type: 数据库类型（'postgresql', 'mysql', 'sqlite'），用于生成对应的 SQL
        """
        if tables_dir:
            self.tables_dir = tables_dir
        else:
            # 默认指向 core/tables（sys_ 前缀表定义在此）
            self.tables_dir = str(PathManager.core() / 'tables')
        # is_verbose 参数仅用于向后兼容，实际详细程度由 logging 配置控制
        self.is_verbose = is_verbose
        self.database_type = database_type or 'postgresql'  # 默认 PostgreSQL
        
        # 缓存已加载的 schema（key 为 schema["name"]，即表名）
        self._schema_cache = {}
        
        # 注册的自定义表（策略表）
        self.registered_tables = {}
    
    # ==================== Schema 加载 ====================
    
    def load_schema_from_python(self, schema_file: str) -> Dict:
        """
        从 Python 文件（schema.py）加载 schema。
        文件内需定义变量 schema（dict）。
        
        Args:
            schema_file: schema.py 文件路径
            
        Returns:
            schema 字典
        """
        schema_path = Path(schema_file).resolve()
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema 文件不存在: {schema_file}")
        
        spec = importlib.util.spec_from_file_location("_schema_module", schema_path)
        if spec is None or spec.loader is None:
            raise ValueError(f"无法加载模块: {schema_file}")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        
        if not hasattr(mod, "schema"):
            raise ValueError(f"Schema 文件缺少变量 'schema': {schema_file}")
        schema = getattr(mod, "schema")
        if not isinstance(schema, dict):
            raise ValueError(f"schema 必须为 dict: {schema_file}")
        
        self._validate_schema(schema)
        return schema
    
    def load_all_schemas(self) -> Dict[str, Dict]:
        """
        递归加载 tables_dir 下所有 schema.py，使用 schema["name"] 作为 key 并写入 _schema_cache。
        
        Returns:
            {table_name: schema_dict}，table_name 即 schema["name"]
        """
        tables_path = Path(self.tables_dir)
        if not tables_path.exists():
            logger.warning(f"⚠️  Schema 目录不存在: {self.tables_dir}")
            return {}
        
        schemas = {}
        for schema_py in sorted(tables_path.rglob("schema.py")):
            if not schema_py.is_file():
                continue
            try:
                schema = self.load_schema_from_python(str(schema_py))
                if schema:
                    table_name = schema["name"]
                    schemas[table_name] = schema
                    self._schema_cache[table_name] = schema
            except Exception as e:
                logger.error(f"❌ 加载 schema 失败 {schema_py}: {e}")
        
        return schemas
    
    def load_schema_from_file(self, schema_file: str) -> Dict:
        """
        从文件加载 schema
        
        Args:
            schema_file: schema.json 文件路径（可以是字符串或 Path）
            
        Returns:
            schema 字典
        """
        # 使用 FileManager 读取文件
        schema_path = Path(schema_file)
        content = FileManager.read_file(schema_path, encoding='utf-8')
        
        if content is None:
            raise FileNotFoundError(f"Schema 文件不存在: {schema_file}")
        
        schema = json.loads(content)
        
        # 验证 schema
        self._validate_schema(schema)
        
        return schema
    
    def _validate_schema(self, schema: Dict):
        """
        验证 schema 格式
        
        Args:
            schema: schema 字典
            
        Raises:
            ValueError: schema 格式错误
        """
        required_fields = ['name', 'fields']
        for field in required_fields:
            if field not in schema:
                raise ValueError(f"Schema 缺少必需字段: {field}")
        
        # 验证字段定义（使用 Field 对象进行验证）
        for field_dict in schema['fields']:
            if 'name' not in field_dict or 'type' not in field_dict:
                raise ValueError(f"字段定义缺少 name 或 type: {field_dict}")
            
            # 使用 Field.from_dict() 进行验证（会抛出异常如果定义无效）
            try:
                Field.from_dict(field_dict)
            except ValueError as e:
                raise ValueError(f"字段 '{field_dict.get('name', 'unknown')}' 定义无效: {e}")
    
    # ==================== SQL 生成 ====================
    
    def generate_create_table_sql(self, schema: Dict) -> str:
        """
        根据 schema 生成 CREATE TABLE SQL（支持多种数据库）
        
        Args:
            schema: schema 字典
            
        Returns:
            CREATE TABLE SQL 语句
        """
        table_name = schema['name']
        fields = schema['fields']
        primary_key = schema.get('primaryKey')
        
        # 验证 fields 是列表类型
        if not isinstance(fields, list):
            raise ValueError(
                f"Schema '{table_name}' 的 'fields' 必须是列表类型，"
                f"但得到 {type(fields).__name__}: {fields}. "
                f"这可能是参数传递错误导致的。"
            )
        
        # 将字段字典转换为 Field 对象
        field_objects = []
        for field_dict in fields:
            try:
                field_obj = Field.from_dict(field_dict)
                field_objects.append(field_obj)
            except Exception as e:
                raise ValueError(f"字段 '{field_dict.get('name', 'unknown')}' 定义无效: {e}")
        
        # 构建字段定义
        field_defs = []
        comments = []  # 存储 COMMENT 语句（PostgreSQL/MySQL）
        
        for field_obj in field_objects:
            # 生成字段 SQL（包含字段名）
            field_sql = f"{field_obj.name} {field_obj.to_sql(self.database_type)}"
            field_sql += field_obj.get_not_null_sql()
            field_sql += field_obj.get_default_sql(self.database_type)
            field_defs.append(field_sql)
            
            # 处理 COMMENT（PostgreSQL/MySQL）
            if field_obj.comment and self.database_type in ['postgresql', 'mysql']:
                if self.database_type == 'postgresql':
                    # 转义单引号：PostgreSQL 中单引号需要转义为两个单引号
                    escaped_comment = field_obj.comment.replace("'", "''")
                    comments.append(f"COMMENT ON COLUMN {table_name}.{field_obj.name} IS '{escaped_comment}';")
        
        # 添加主键（如果字段定义中没有包含）
        if primary_key:
            # 检查是否已经有 AUTO_INCREMENT 主键（SQLite）
            has_auto_inc_pk = False
            if self.database_type == 'sqlite':
                for field_obj in field_objects:
                    if field_obj.auto_increment:
                        pk_list = primary_key if isinstance(primary_key, list) else [primary_key]
                        if field_obj.name in pk_list:
                            has_auto_inc_pk = True
                            break
            
            if not has_auto_inc_pk:
                pk_def = self._generate_primary_key_definition(primary_key)
                field_defs.append(pk_def)
        
        # 生成完整 SQL
        fields_sql = ',\n    '.join(field_defs)
        create_sql = f"CREATE TABLE IF NOT EXISTS {table_name} (\n    {fields_sql}\n);"
        
        # 添加 COMMENT 语句（PostgreSQL）
        if comments:
            create_sql += "\n" + "\n".join(comments)
        
        return create_sql.strip()
    
    def _generate_primary_key_definition(self, primary_key) -> str:
        """
        生成主键定义（支持多种数据库）
        
        Args:
            primary_key: 主键字段（字符串或列表）
            
        Returns:
            PRIMARY KEY SQL 定义
        """
        if isinstance(primary_key, list):
            pk_fields = ', '.join([f"{f}" for f in primary_key])
            return f"PRIMARY KEY ({pk_fields})"
        else:
            return f"PRIMARY KEY ({primary_key})"
    
    def generate_create_index_sql(self, table_name: str, index: Dict) -> str:
        """
        生成创建索引的 SQL
        
        Args:
            table_name: 表名
            index: 索引定义
            
        Returns:
            CREATE INDEX SQL 语句
        """
        index_name = index['name']
        index_fields = index['fields']
        is_unique = index.get('unique', False)
        
        unique_keyword = 'UNIQUE' if is_unique else ''
        
        # 根据数据库类型处理标识符引用
        if self.database_type == 'postgresql':
            # PostgreSQL 使用双引号
            fields_str = ', '.join([f'"{f}"' if f.lower() in ['key', 'value', 'order', 'group'] else f for f in index_fields])
            table_name_quoted = f'"{table_name}"' if table_name.lower() in ['key', 'value', 'order', 'group'] else table_name
            index_name_quoted = f'"{index_name}"' if index_name.lower() in ['key', 'value', 'order', 'group'] else index_name
        elif self.database_type == 'mysql':
            # MySQL 使用反引号
            fields_str = ', '.join([f'`{f}`' if f.lower() in ['key', 'value', 'order', 'group'] else f for f in index_fields])
            table_name_quoted = f'`{table_name}`' if table_name.lower() in ['key', 'value', 'order', 'group'] else table_name
            index_name_quoted = f'`{index_name}`' if index_name.lower() in ['key', 'value', 'order', 'group'] else index_name
        else:
            # SQLite 通常不需要引号，但为了安全也可以使用双引号
            fields_str = ', '.join(index_fields)
            table_name_quoted = table_name
            index_name_quoted = index_name
        
        sql = f"CREATE {unique_keyword} INDEX IF NOT EXISTS {index_name_quoted} ON {table_name_quoted} ({fields_str})"
        return sql
    
    # ==================== 表创建 ====================
    
    def create_table(self, schema: Dict, get_connection_func: Callable):
        """
        创建表（包含索引）
        
        Args:
            schema: schema 字典
            get_connection_func: 获取数据库连接的函数（上下文管理器）
        """
        # 验证参数类型
        if not isinstance(schema, dict):
            raise TypeError(
                f"create_table 的 schema 参数必须是字典类型，"
                f"但得到 {type(schema).__name__}: {schema}. "
                f"这可能是参数传递错误导致的。"
            )
        if not callable(get_connection_func):
            raise TypeError(
                f"create_table 的 get_connection_func 参数必须是可调用对象，"
                f"但得到 {type(get_connection_func).__name__}: {get_connection_func}."
            )
        
        table_name = schema.get('name')
        if not table_name:
            raise ValueError(f"Schema 缺少 'name' 字段: {schema}")
        
        # 生成 CREATE TABLE SQL
        create_sql = self.generate_create_table_sql(schema)
        
        # 执行创建表
        with get_connection_func() as conn:
            conn.execute(create_sql)
        
        logger.debug(f"✅ 表 '{table_name}' 创建成功")
        
        # 创建索引
        indexes = schema.get('indexes', [])
        if indexes:
            self.create_indexes(table_name, indexes, get_connection_func)
    
    def create_indexes(self, table_name: str, indexes: List[Dict], get_connection_func: Callable):
        """
        创建索引
        
        Args:
            table_name: 表名
            indexes: 索引定义列表
            get_connection_func: 获取数据库连接的函数（上下文管理器）
        """
        for index in indexes:
            try:
                index_sql = self.generate_create_index_sql(table_name, index)
                with get_connection_func() as conn:
                    conn.execute(index_sql)
                logger.debug(f"✅ 索引 '{index['name']}' 创建成功")
            except Exception as e:
                logger.error(f"❌ 创建索引失败 '{index['name']}': {e}")
    
    def create_table_with_indexes(self, schema: Dict, get_connection_func: Callable):
        """
        创建表和索引（便捷方法）
        
        Args:
            schema: schema 字典
            get_connection_func: 获取数据库连接的函数（上下文管理器）
        """
        self.create_table(schema, get_connection_func)
    
    def create_all_tables(self, get_connection_func: Callable):
        """
        创建所有已加载的 schema 表
        
        Args:
            get_connection_func: 获取数据库连接的函数（上下文管理器）
        """
        schemas = self.load_all_schemas()
        for table_name, schema in schemas.items():
            try:
                self.create_table_with_indexes(schema, get_connection_func)
            except Exception as e:
                logger.error(f"❌ 创建表失败 '{table_name}': {e}")
    
    # ==================== 表注册和查询 ====================
    
    def register_table(self, table_name: str, schema: Dict):
        """
        注册自定义表（给策略用）
        
        Args:
            table_name: 表名
            schema: 表的 schema 定义
        """
        self.registered_tables[table_name] = schema
        logger.debug(f"✅ 表 '{table_name}' 已注册")
    
    def create_registered_tables(self, get_connection_func: Callable):
        """
        创建所有注册的表（策略表）
        
        Args:
            get_connection_func: 获取数据库连接的函数（上下文管理器）
        """
        for table_name, schema in self.registered_tables.items():
            try:
                self.create_table_with_indexes(schema, get_connection_func)
            except Exception as e:
                logger.error(f"❌ 创建注册表失败 '{table_name}': {e}")
    
    def is_table_exists(self, table_name: str, adapter) -> bool:
        """
        检查表是否存在
        
        Args:
            table_name: 表名
            adapter: 数据库适配器（有 is_table_exists 方法）
            
        Returns:
            是否存在
        """
        if not adapter:
            raise RuntimeError("Adapter is required to check table existence")
        
        try:
            return adapter.is_table_exists(table_name)
        except Exception as e:
            logger.error(f"检查表是否存在失败: {e}")
            return False
    
    def get_table_schema(self, table_name: str) -> Optional[Dict]:
        """
        获取表的 schema。
        表名即 schema["name"]（如 sys_stock_list），与目录名可能不同。
        
        Args:
            table_name: 表名
            
        Returns:
            schema 字典，不存在返回 None
        """
        # 先从缓存查找
        if table_name in self._schema_cache:
            return self._schema_cache[table_name]
        
        # 从注册表查找
        if table_name in self.registered_tables:
            return self.registered_tables[table_name]
        
        # 通过 load_all_schemas 拉取并缓存（按 schema["name"] 索引）
        self.load_all_schemas()
        return self._schema_cache.get(table_name)
    
    def get_table_fields(self, table_name: str) -> List[str]:
        """
        获取表的所有字段名
        
        Args:
            table_name: 表名
            
        Returns:
            字段名列表
        """
        schema = self.get_table_schema(table_name)
        if not schema:
            return []
        
        return [field['name'] for field in schema['fields']]
    
    def clear_cache(self):
        """清空 schema 缓存"""
        self._schema_cache.clear()
