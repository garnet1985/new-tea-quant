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
    
    def __init__(self, tables_dir: str = None, is_verbose: bool = False, database_type: str = None):
        """
        初始化 DbSchemaManager
        
        Args:
            tables_dir: schema 文件目录（默认为 app/data_manager/base_tables）
            is_verbose: 是否输出详细日志
            database_type: 数据库类型（'postgresql', 'mysql', 'sqlite'），用于生成对应的 SQL
        """
        if tables_dir:
            self.tables_dir = tables_dir
        else:
            # 默认指向 app/core/modules/data_manager/base_tables
            # 从 app/core/infra/db 向上找到项目根，再定位到 app/core/modules/data_manager/base_tables
            current_dir = os.path.dirname(__file__)  # app/core/infra/db
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))  # 项目根
            self.tables_dir = os.path.join(project_root, 'app', 'core', 'modules', 'data_manager', 'base_tables')
        self.is_verbose = is_verbose
        self.database_type = database_type or 'postgresql'  # 默认 PostgreSQL
        
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
        根据 schema 生成 CREATE TABLE SQL（支持多种数据库）
        
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
        comments = []  # 存储 COMMENT 语句（PostgreSQL/MySQL）
        
        for field in fields:
            field_def = self._generate_field_definition(field)
            field_defs.append(field_def)
            
            # 处理 COMMENT（PostgreSQL/MySQL）
            comment = field.get('comment')
            if comment and self.database_type in ['postgresql', 'mysql']:
                if self.database_type == 'postgresql':
                    comments.append(f"COMMENT ON COLUMN {table_name}.{field['name']} IS '{comment}';")
                elif self.database_type == 'mysql':
                    # MySQL 的 COMMENT 在字段定义中，已经在 _generate_field_definition 中处理
                    # 但 MySQL 不支持单独的 COMMENT ON COLUMN，所以这里不需要额外处理
                    pass
        
        # 添加主键（如果字段定义中没有包含）
        if primary_key:
            # 检查是否已经有 AUTO_INCREMENT 主键（SQLite）
            has_auto_inc_pk = False
            if self.database_type == 'sqlite':
                for field in fields:
                    if field.get('autoIncrement') or field.get('isAutoIncrement'):
                        if field['name'] in (primary_key if isinstance(primary_key, list) else [primary_key]):
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
        
        # 处理字段类型（根据数据库类型）
        type_def = self._map_field_type(field_type, field)
        
        # 构建字段定义
        field_def = f"{field_name} {type_def}"
        
        # 处理 AUTO_INCREMENT（根据数据库类型）
        if is_auto_increment:
            auto_inc_def = self._get_auto_increment_definition()
            if auto_inc_def:
                field_def = f"{field_name} {auto_inc_def}"
                # AUTO_INCREMENT 字段通常也是主键，不需要额外的 NOT NULL
                is_required = False
        
        # 处理 NOT NULL
        if is_required:
            field_def += " NOT NULL"
        
        # 处理默认值
        if default_value is not None:
            # 处理 MySQL 的 ON UPDATE CURRENT_TIMESTAMP 语法
            # PostgreSQL/SQLite 不支持 ON UPDATE，只保留 CURRENT_TIMESTAMP
            if isinstance(default_value, str):
                default_upper = default_value.upper()
                # 移除 ON UPDATE CURRENT_TIMESTAMP 部分
                if 'ON UPDATE CURRENT_TIMESTAMP' in default_upper:
                    # 提取 CURRENT_TIMESTAMP 部分
                    if 'CURRENT_TIMESTAMP' in default_upper:
                        default_value = 'CURRENT_TIMESTAMP'
                    else:
                        # 如果只有 ON UPDATE，移除它
                        default_value = default_value.split(' ON UPDATE')[0].strip()
                        if not default_value:
                            default_value = None
                
                # 处理标准的时间戳默认值
                if default_value and default_value.upper() in ['CURRENT_TIMESTAMP', 'CURRENT_DATE']:
                    field_def += f" DEFAULT {default_value}"
                elif default_value:
                    # 根据原始字段类型决定是否加引号
                    if field_type in ['VARCHAR', 'TEXT', 'CHAR', 'DATE', 'DATETIME', 'TIME', 'TIMESTAMP']:
                        field_def += f" DEFAULT '{default_value}'"
                    else:
                        field_def += f" DEFAULT {default_value}"
            else:
                # 非字符串默认值
                if field_type in ['VARCHAR', 'TEXT', 'CHAR', 'DATE', 'DATETIME', 'TIME', 'TIMESTAMP']:
                    field_def += f" DEFAULT '{default_value}'"
                else:
                    field_def += f" DEFAULT {default_value}"
        
        # 处理 COMMENT（根据数据库类型）
        comment = field.get('comment')
        if comment and self.database_type in ['postgresql', 'mysql']:
            # COMMENT 在 CREATE TABLE 后单独添加（PostgreSQL/MySQL）
            # 这里先返回字段定义，COMMENT 在 generate_create_table_sql 中处理
            pass
        
        return field_def
    
    def _map_field_type(self, field_type: str, field: Dict) -> str:
        """
        根据数据库类型映射字段类型
        
        Args:
            field_type: 原始字段类型
            field: 字段定义字典
            
        Returns:
            映射后的字段类型 SQL
        """
        field_type = field_type.upper()
        
        # VARCHAR 类型
        if field_type == 'VARCHAR' and 'length' in field:
            return f"VARCHAR({field['length']})"
        
        # TEXT 类型
        if field_type == 'TEXT':
            if self.database_type == 'sqlite':
                return "TEXT"  # SQLite 支持 TEXT
            elif self.database_type == 'postgresql':
                return "TEXT"  # PostgreSQL 支持 TEXT
            elif self.database_type == 'mysql':
                return "TEXT"  # MySQL 支持 TEXT
            else:
                return "VARCHAR"  # 其他情况使用 VARCHAR
        
        # TINYINT(1) -> BOOLEAN
        if field_type == 'TINYINT' and 'length' in field and field.get('length') == 1:
            if self.database_type == 'postgresql':
                return "BOOLEAN"
            elif self.database_type == 'mysql':
                return "TINYINT(1)"  # MySQL 保留 TINYINT(1)
            elif self.database_type == 'sqlite':
                return "INTEGER"  # SQLite 使用 INTEGER 表示布尔值
            else:
                return "BOOLEAN"
        
        # 其他 TINYINT -> INTEGER
        if field_type == 'TINYINT':
            return "INTEGER"
        
        # DATETIME -> TIMESTAMP
        if field_type == 'DATETIME':
            if self.database_type == 'postgresql':
                return "TIMESTAMP"
            elif self.database_type == 'mysql':
                return "DATETIME"  # MySQL 支持 DATETIME
            elif self.database_type == 'sqlite':
                return "TEXT"  # SQLite 使用 TEXT 存储日期时间
            else:
                return "TIMESTAMP"
        
        # DECIMAL/NUMERIC
        if field_type in ['DECIMAL', 'NUMERIC']:
            if 'length' in field:
                length = field['length']
                if isinstance(length, str):
                    return f"DECIMAL({length})"
                elif isinstance(length, (int, float)):
                    return f"DECIMAL({length})"
            return "DECIMAL"
        
        # 其他类型直接返回
        return field_type
    
    def _get_auto_increment_definition(self) -> Optional[str]:
        """
        根据数据库类型获取 AUTO_INCREMENT 定义
        
        Returns:
            AUTO_INCREMENT SQL 定义，如果数据库不支持则返回 None
        """
        if self.database_type == 'postgresql':
            return "SERIAL"  # PostgreSQL 使用 SERIAL
        elif self.database_type == 'mysql':
            return "INT AUTO_INCREMENT"  # MySQL 使用 AUTO_INCREMENT
        elif self.database_type == 'sqlite':
            return "INTEGER PRIMARY KEY AUTOINCREMENT"  # SQLite 使用 AUTOINCREMENT
        else:
            return None
    
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
    
    # ==================== 表操作（需要数据库连接）====================
    
    def create_table(self, schema: Dict, db_connection):
        """
        创建表（支持多种数据库）
        
        Args:
            schema: schema 字典
            db_connection: 数据库连接（上下文管理器）
                - SQLite: 连接对象可以直接执行 SQL
                - PostgreSQL/MySQL: 连接对象需要使用游标执行 SQL
        """
        table_name = schema['name']
        
        # 生成建表 SQL
        create_sql = self.generate_create_table_sql(schema)
        
        # 执行建表
        with db_connection as conn:
            # 检查连接类型
            # SQLite 连接可以直接执行 SQL
            if hasattr(conn, 'execute') and not hasattr(conn, 'cursor'):
                # SQLite 风格：直接执行
                conn.execute(create_sql)
            else:
                # PostgreSQL/MySQL 风格：使用游标
                # 如果连接有 cursor 方法，使用游标
                if hasattr(conn, 'cursor'):
                    with conn.cursor() as cursor:
                        cursor.execute(create_sql)
                    conn.commit()
                else:
                    # 尝试直接执行（可能是包装的连接对象）
                    conn.execute(create_sql)
        
        if self.is_verbose:
            logger.debug(f"✅ 表 {table_name} 已创建/验证")
    
    def create_indexes(self, table_name: str, indexes: List[Dict], db_connection):
        """
        创建索引（支持多种数据库）
        
        Args:
            table_name: 表名
            indexes: 索引定义列表
            db_connection: 数据库连接（上下文管理器）
        """
        if not indexes:
            return
        
        # 生成并执行索引创建 SQL
        with db_connection as conn:
            for index in indexes:
                # 使用 generate_create_index_sql 生成 SQL（会根据数据库类型生成正确的 SQL）
                sql = self.generate_create_index_sql(table_name, index)
                
                try:
                    # 检查连接类型
                    if hasattr(conn, 'execute') and not hasattr(conn, 'cursor'):
                        # SQLite 风格：直接执行
                        conn.execute(sql)
                    else:
                        # PostgreSQL/MySQL 风格：使用游标
                        if hasattr(conn, 'cursor'):
                            with conn.cursor() as cursor:
                                cursor.execute(sql)
                            conn.commit()
                        else:
                            conn.execute(sql)
                    
                    if self.is_verbose:
                        logger.debug(f"✅ 创建索引: {table_name}.{index['name']}")
                except Exception as e:
                    logger.warning(f"⚠️  创建索引失败 {table_name}.{index['name']}: {e}")
    
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
        检查表是否存在（支持多种数据库）
        
        Args:
            table_name: 表名
            database: 数据库名（某些数据库不需要，已忽略）
            db_connection: 数据库连接（上下文管理器）
            
        Returns:
            是否存在
        """
        # 根据数据库类型生成不同的 SQL
        if self.database_type == 'sqlite':
            sql = """
            SELECT COUNT(*) as count 
            FROM sqlite_master 
            WHERE type='table' AND name = ?
            """
            params = (table_name,)
        elif self.database_type == 'postgresql':
            sql = """
            SELECT COUNT(*) as count 
            FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = %s
            """
            params = (table_name,)
        elif self.database_type == 'mysql':
            sql = """
            SELECT COUNT(*) as count 
            FROM information_schema.tables 
            WHERE table_schema = DATABASE() AND table_name = %s
            """
            params = (table_name,)
        else:
            # 默认使用 PostgreSQL 语法
            sql = """
            SELECT COUNT(*) as count 
            FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = %s
            """
            params = (table_name,)
        
        with db_connection as conn:
            # 检查连接类型
            if hasattr(conn, 'execute') and not hasattr(conn, 'cursor'):
                # SQLite 风格：直接执行
                sql = sql.replace("%s", "?")
                result = conn.execute(sql, params).fetchone()
            else:
                # PostgreSQL/MySQL 风格：使用游标
                if hasattr(conn, 'cursor'):
                    with conn.cursor() as cursor:
                        cursor.execute(sql, params)
                        result = cursor.fetchone()
                else:
                    result = conn.execute(sql, params).fetchone()
            
            # 处理结果
            if result:
                if isinstance(result, dict):
                    return result.get('count', 0) > 0
                elif isinstance(result, (list, tuple)):
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

