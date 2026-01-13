"""
DbSchemaManager - Schema 管理器，负责数据库表结构的管理
- 加载 schema.json 文件
- 生成建表 SQL
- 创建表和索引
- 管理策略自定义表
"""
import os
import json
from typing import Dict, List, Optional
from loguru import logger


class DbSchemaManager:
    """
    Schema 管理器
    
    职责：
    - 从文件系统加载 schema.json
    - 根据 schema 生成 CREATE TABLE SQL
    - 创建表和索引
    - 管理策略自定义表的注册
    
    不负责：
    - 数据库连接（由 DatabaseManager 提供）
    - 数据查询和写入
    """
    
    def __init__(self, tables_dir: str = None, charset: str = 'utf8mb4', is_verbose: bool = False):
        """
        初始化 DbSchemaManager
        
        Args:
            tables_dir: schema 文件目录（默认为 app/data_manager/base_tables）
            charset: 数据库字符集
            is_verbose: 是否输出详细日志
        """
        if tables_dir:
            self.tables_dir = tables_dir
        else:
            # 默认指向 app/core/modules/data_manager/base_tables
            # 从 app/core/infra/db 向上找到项目根，再定位到 app/core/modules/data_manager/base_tables
            current_dir = os.path.dirname(__file__)  # app/core/infra/db
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))  # 项目根
            self.tables_dir = os.path.join(project_root, 'app', 'core', 'modules', 'data_manager', 'base_tables')
        self.charset = charset
        self.is_verbose = is_verbose
        
        # 缓存已加载的 schema
        self._schema_cache = {}
        
        # 注册的自定义表（策略表）
        self.registered_tables = {}
    
    
    # ==================== Schema 加载 ====================
    
    def load_all_schemas(self) -> Dict[str, Dict]:
        """
        加载所有 schema
        
        Returns:
            {table_name: schema_dict}
        """
        if not os.path.exists(self.tables_dir):
            logger.warning(f"⚠️  Schema 目录不存在: {self.tables_dir}")
            return {}
        
        schemas = {}
        for table_name in os.listdir(self.tables_dir):
            table_dir = os.path.join(self.tables_dir, table_name)
            schema_file = os.path.join(table_dir, 'schema.json')
            
            if os.path.isdir(table_dir) and os.path.exists(schema_file):
                try:
                    schema = self.load_schema_from_file(schema_file)
                    schemas[table_name] = schema
                except Exception as e:
                    logger.error(f"❌ 加载 schema 失败 {table_name}: {e}")
        
        return schemas
    
    def load_schema_from_file(self, schema_file: str) -> Dict:
        """
        从文件加载 schema
        
        Args:
            schema_file: schema.json 文件路径
            
        Returns:
            schema 字典
        """
        with open(schema_file, 'r', encoding='utf-8') as f:
            schema = json.load(f)
        
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
        
        # 验证字段定义
        for field in schema['fields']:
            if 'name' not in field or 'type' not in field:
                raise ValueError(f"字段定义缺少 name 或 type: {field}")
    
    # ==================== SQL 生成 ====================
    
    def generate_create_table_sql(self, schema: Dict) -> str:
        """
        根据 schema 生成 CREATE TABLE SQL
        
        Args:
            schema: schema 字典
            
        Returns:
            CREATE TABLE SQL 语句
        """
        table_name = schema['name']
        fields = schema['fields']
        primary_key = schema.get('primaryKey')
        
        # 构建字段定义
        field_defs = []
        for field in fields:
            field_def = self._generate_field_definition(field)
            field_defs.append(field_def)
        
        # 添加主键
        if primary_key:
            pk_def = self._generate_primary_key_definition(primary_key)
            field_defs.append(pk_def)
        
        # 生成完整 SQL（DuckDB 版本，去掉 MySQL 特有的 ENGINE 和 CHARSET）
        fields_sql = ',\n    '.join(field_defs)
        create_sql = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                {fields_sql}
            );
            """
        
        return create_sql.strip()
    
    def _generate_field_definition(self, field: Dict) -> str:
        """
        生成字段定义
        
        Args:
            field: 字段定义字典
            
        Returns:
            字段 SQL 定义
        """
        field_name = field['name']
        field_type = field['type'].upper()
        is_required = field.get('isRequired', False)
        # 支持两种命名：autoIncrement 和 isAutoIncrement
        is_auto_increment = field.get('autoIncrement', False) or field.get('isAutoIncrement', False)
        default_value = field.get('default')
        
        # 处理字段类型（DuckDB 版本）
        # 类型映射：TINYINT(1) -> BOOLEAN, TEXT -> VARCHAR
        if field_type == 'VARCHAR' and 'length' in field:
            type_def = f"VARCHAR({field['length']})"
        elif field_type == 'TEXT':
            type_def = "VARCHAR"  # DuckDB 使用 VARCHAR 替代 TEXT
        elif field_type == 'TINYINT' and 'length' in field and field.get('length') == 1:
            type_def = "BOOLEAN"  # TINYINT(1) -> BOOLEAN
        elif field_type == 'TINYINT':
            type_def = "INTEGER"  # 其他 TINYINT -> INTEGER
        elif field_type == 'DATETIME':
            type_def = "TIMESTAMP"  # DATETIME -> TIMESTAMP
        else:
            type_def = field_type
        
        # 构建字段定义（DuckDB 不需要反引号，但保留以兼容）
        field_def = f"{field_name} {type_def}"
        
        # DuckDB 不支持 AUTO_INCREMENT，忽略该属性
        # 处理 NOT NULL
        if is_required:
            field_def += " NOT NULL"
        
        # 处理默认值
        if default_value is not None:
            # 一些函数类默认值直接写（CURRENT_TIMESTAMP 等）
            if isinstance(default_value, str) and default_value.upper() in ['CURRENT_TIMESTAMP', 'CURRENT_DATE']:
                field_def += f" DEFAULT {default_value}"
            else:
                # 根据原始字段类型决定是否加引号
                # 注意这里用的是 field_type（去掉长度信息），而不是 type_def
                if field_type in ['VARCHAR', 'TEXT', 'CHAR', 'DATE', 'DATETIME', 'TIME', 'TIMESTAMP']:
                    field_def += f" DEFAULT '{default_value}'"
                else:
                    field_def += f" DEFAULT {default_value}"
        
        # DuckDB 不支持 COMMENT，忽略
        
        return field_def
    
    def _generate_primary_key_definition(self, primary_key) -> str:
        """
        生成主键定义（DuckDB 版本）
        
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
        fields_str = ', '.join([f"`{f}`" for f in index_fields])
        
        sql = f"CREATE {unique_keyword} INDEX `{index_name}` ON `{table_name}` ({fields_str})"
        return sql
    
    # ==================== 表操作（需要数据库连接）====================
    
    def create_table(self, schema: Dict, db_connection):
        """
        创建表（DuckDB 版本）
        
        Args:
            schema: schema 字典
            db_connection: 数据库连接（上下文管理器，DuckDB 连接）
        """
        table_name = schema['name']
        
        # 生成建表 SQL
        create_sql = self.generate_create_table_sql(schema)
        
        # 执行建表（DuckDB 连接可以直接执行 SQL）
        with db_connection as conn:
            conn.execute(create_sql)
        
        if self.is_verbose:
            logger.debug(f"✅ 表 {table_name} 已创建/验证")
    
    def create_indexes(self, table_name: str, indexes: List[Dict], db_connection):
        """
        创建索引（DuckDB 版本）
        
        注意：DuckDB 的索引机制与 MySQL 不同，暂时跳过索引创建
        后续如果需要，可以基于 DuckDB 的 CREATE INDEX 语法实现
        
        Args:
            table_name: 表名
            indexes: 索引定义列表
            db_connection: 数据库连接（上下文管理器）
        """
        # DuckDB 支持 CREATE INDEX，但语法和 MySQL 略有不同
        # 暂时跳过索引创建，依赖主键和列式存储的性能优势
        if self.is_verbose and indexes:
            logger.debug(f"⚠️  跳过索引创建（DuckDB 暂不支持自动创建索引）: {table_name}")
        
        # 如果需要创建索引，可以这样实现：
        # with db_connection as conn:
        #     for index in indexes:
        #         index_name = index['name']
        #         index_fields = index['fields']
        #         is_unique = index.get('unique', False)
        #         unique_keyword = 'UNIQUE' if is_unique else ''
        #         fields_str = ', '.join(index_fields)
        #         sql = f"CREATE {unique_keyword} INDEX IF NOT EXISTS {index_name} ON {table_name} ({fields_str})"
        #         try:
        #             conn.execute(sql)
        #             if self.is_verbose:
        #                 logger.debug(f"✅ 创建索引: {table_name}.{index_name}")
        #         except Exception as e:
        #             logger.warning(f"⚠️  创建索引失败 {table_name}.{index_name}: {e}")
    
    def create_table_with_indexes(self, schema: Dict, db_connection_func):
        """
        创建表及其索引
        
        Args:
            schema: schema 字典
            db_connection_func: 获取数据库连接的函数（返回上下文管理器）
        """
        table_name = schema['name']
        
        # 创建表
        self.create_table(schema, db_connection_func())
        
        # 创建索引
        if 'indexes' in schema:
            self.create_indexes(table_name, schema['indexes'], db_connection_func())
    
    def create_all_tables(self, get_connection_func):
        """
        创建所有表（从 tables 目录）
        
        Args:
            get_connection_func: 获取数据库连接的函数（返回上下文管理器）
            
        Returns:
            成功创建的表数量
        """
        schemas = self.load_all_schemas()
        created_count = 0
        
        for table_name, schema in schemas.items():
            try:
                self.create_table_with_indexes(schema, get_connection_func)
                created_count += 1
            except Exception as e:
                logger.error(f"❌ 创建表失败 {table_name}: {e}")
        
        if self.is_verbose:
            logger.info(f"✅ 成功创建/检查 {created_count} 个表")
        
        return created_count
    
    # ==================== 策略表注册 ====================
    
    def register_table(self, table_name: str, schema: Dict):
        """
        注册自定义表（给策略用）
        
        Args:
            table_name: 表名
            schema: 表的 schema 定义
        """
        # 验证 schema
        self._validate_schema(schema)
        
        # 注册
        self.registered_tables[table_name] = schema
        
        if self.is_verbose:
            logger.debug(f"✅ 注册策略表: {table_name}")
    
    def create_registered_tables(self, get_connection_func):
        """
        创建所有注册的表（策略表）
        
        Args:
            get_connection_func: 获取数据库连接的函数
        """
        for table_name, schema in self.registered_tables.items():
            try:
                self.create_table_with_indexes(schema, get_connection_func())
                if self.is_verbose:
                    logger.info(f"✅ 创建策略表: {table_name}")
            except Exception as e:
                logger.error(f"❌ 创建策略表失败 {table_name}: {e}")
    
    # ==================== 工具方法 ====================
    
    def is_table_exists(self, table_name: str, database: str, db_connection) -> bool:
        """
        检查表是否存在（DuckDB 版本）
        
        Args:
            table_name: 表名
            database: 数据库名（DuckDB 不需要，保留参数兼容）
            db_connection: 数据库连接（上下文管理器）
            
        Returns:
            是否存在
        """
        sql = """
        SELECT COUNT(*) as count 
        FROM information_schema.tables 
        WHERE table_name = ?
        """
        
        with db_connection as conn:
            result = conn.execute(sql, (table_name,)).fetchone()
            # DuckDB 返回的是元组，需要转换为字典或直接访问
            if result:
                if isinstance(result, dict):
                    return result.get('count', 0) > 0
                else:
                    # 元组格式，第一个元素是 count
                    return result[0] > 0
            return False
    
    def get_table_schema(self, table_name: str) -> Optional[Dict]:
        """
        获取表的 schema
        
        Args:
            table_name: 表名
            
        Returns:
            schema 字典，不存在返回 None
        """
        # 先从缓存查找
        if table_name in self._schema_cache:
            return self._schema_cache[table_name]
        
        # 从文件加载
        schema_file = os.path.join(self.tables_dir, table_name, 'schema.json')
        if os.path.exists(schema_file):
            schema = self.load_schema_from_file(schema_file)
            self._schema_cache[table_name] = schema
            return schema
        
        # 从注册表查找
        if table_name in self.registered_tables:
            return self.registered_tables[table_name]
        
        return None
    
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

