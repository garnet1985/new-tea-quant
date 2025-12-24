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
            # 默认指向 app/data_manager/base_tables
            # 从 utils/db 向上找到项目根，再定位到 app/data_manager/base_tables
            current_dir = os.path.dirname(__file__)  # utils/db
            project_root = os.path.dirname(os.path.dirname(current_dir))  # 项目根
            self.tables_dir = os.path.join(project_root, 'app', 'data_manager', 'base_tables')
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
        
        # 生成完整 SQL
        fields_sql = ',\n    '.join(field_defs)
        create_sql = f"""
CREATE TABLE IF NOT EXISTS `{table_name}` (
    {fields_sql}
) ENGINE=InnoDB DEFAULT CHARSET={self.charset} COLLATE={self.charset}_general_ci
"""
        
        return create_sql
    
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
        
        # 处理字段类型
        if field_type == 'VARCHAR' and 'length' in field:
            type_def = f"{field_type}({field['length']})"
        elif field_type == 'TINYINT':
            type_def = f"{field_type}(1)"
        else:
            type_def = field_type
        
        # 构建字段定义（字段名用反引号包裹，避免 SQL 关键字冲突）
        field_def = f"`{field_name}` {type_def}"
        field_def += " NOT NULL" if is_required else " NULL"
        
        # 添加注释（转义单引号）
        if 'description' in field:
            desc = field['description'].replace("'", "\\'")
            field_def += f" COMMENT '{desc}'"
        
        return field_def
    
    def _generate_primary_key_definition(self, primary_key) -> str:
        """
        生成主键定义
        
        Args:
            primary_key: 主键字段（字符串或列表）
            
        Returns:
            PRIMARY KEY SQL 定义
        """
        if isinstance(primary_key, list):
            pk_fields = ', '.join([f"`{f}`" for f in primary_key])
            return f"PRIMARY KEY ({pk_fields})"
        else:
            return f"PRIMARY KEY (`{primary_key}`)"
    
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
        创建表
        
        Args:
            schema: schema 字典
            db_connection: 数据库连接（上下文管理器）
        """
        table_name = schema['name']
        
        # 生成建表 SQL
        create_sql = self.generate_create_table_sql(schema)
        
        # 执行建表
        with db_connection as conn:
            with conn.cursor() as cursor:
                cursor.execute(create_sql)
        
        if self.is_verbose:
            logger.debug(f"✅ 表 {table_name} 已创建/验证")
    
    def create_indexes(self, table_name: str, indexes: List[Dict], db_connection):
        """
        创建索引
        
        Args:
            table_name: 表名
            indexes: 索引定义列表
            db_connection: 数据库连接（上下文管理器）
        """
        with db_connection as conn:
            with conn.cursor() as cursor:
                for index in indexes:
                    index_name = index['name']
                    
                    # 检查索引是否存在
                    cursor.execute(f"SHOW INDEX FROM `{table_name}` WHERE Key_name = %s", (index_name,))
                    if cursor.fetchone():
                        continue  # 索引已存在
                    
                    # 创建索引
                    try:
                        sql = self.generate_create_index_sql(table_name, index)
                        cursor.execute(sql)
                        
                        if self.is_verbose:
                            logger.debug(f"✅ 创建索引: {table_name}.{index_name}")
                    except Exception as e:
                        logger.warning(f"⚠️  创建索引失败 {table_name}.{index_name}: {e}")
    
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
        检查表是否存在
        
        Args:
            table_name: 表名
            database: 数据库名
            db_connection: 数据库连接（上下文管理器）
            
        Returns:
            是否存在
        """
        sql = """
        SELECT COUNT(*) as count 
        FROM information_schema.tables 
        WHERE table_schema = %s AND table_name = %s
        """
        
        with db_connection as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, [database, table_name])
                result = cursor.fetchone()
                return result['count'] > 0 if result else False
    
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

