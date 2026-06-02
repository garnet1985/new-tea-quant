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
from typing import Any, Dict, List, Optional, Callable, Set
from pathlib import Path

from core.infra.project_context import PathManager, FileManager
from core.infra.db.helpers.db_helpers import DBHelper
from core.infra.db.schema_management.field import Field
from core.infra.db.storage_registry import normalize_storage_domain
from core.infra.db.engines.schema_parser_factory import get_schema_parser
from core.infra.db.engines._shared.schema_parser_base import SchemaParserBase
from core.infra.db.engines._shared.ddl_executor import execute_ddl
from core.infra.db.engines._shared.schema_introspection import fetch_column_names


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
            database_type: 数据库类型（'postgresql', 'mysql'），用于生成对应的 SQL
        """
        if tables_dir:
            self.tables_dir = tables_dir
        else:
            # 默认指向 core/tables（sys_ 前缀表定义在此）
            self.tables_dir = str(PathManager.core() / 'tables')
        self.is_verbose = is_verbose
        self.database_type = database_type or 'postgresql'  # 默认 PostgreSQL
        
        # 缓存已加载的 schema（key 为 schema["name"]，即表名）
        self._schema_cache = {}
        
        # 注册的自定义表（策略表）
        self.registered_tables = {}

    @property
    def ddl_database_type(self) -> str:
        """DDL 方言（mysql | postgresql | duckdb）。"""
        return DBHelper.sql_dialect_for_schema({"database_type": self.database_type})

    @staticmethod
    def _duckdb_sequence_name(table_name: str, column_name: str) -> str:
        """DuckDB 自增列配套 sequence 名（表级 CREATE SEQUENCE）。"""
        return SchemaParserBase.duckdb_sequence_name(table_name, column_name)

    def _ddl_parser(self):
        return get_schema_parser(self.ddl_database_type)
    
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
        
        self._validate_schema(schema, schema_path.resolve())
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
        
        self._assert_unique_update_keys(schemas)
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
        self._validate_schema(schema, schema_path.resolve())
        
        return schema
    
    def _requires_update_key(self, schema_file_path: Optional[Path]) -> bool:
        """仅 ``core/tables`` 下的 Python schema 必须带 ``update_key``（迁移/脚本稳定锚点）。"""
        if schema_file_path is None:
            return False
        core_tables = (PathManager.core() / "tables").resolve()
        try:
            schema_file_path.resolve().relative_to(core_tables)
            return True
        except ValueError:
            return False

    def _assert_unique_update_keys(self, schemas: Dict[str, Dict]) -> None:
        """``core/tables`` 中 ``update_key`` 全局唯一。"""
        seen: Dict[str, str] = {}
        for table_name, schema in schemas.items():
            uk = schema.get("update_key")
            if not isinstance(uk, str) or not uk.strip():
                continue
            uk = uk.strip()
            if uk in seen:
                raise ValueError(
                    f"update_key 重复: {uk!r} 被表 {seen[uk]!r} 与 {table_name!r} 同时使用"
                )
            seen[uk] = table_name

    def _validate_schema(self, schema: Dict, schema_file_path: Optional[Path] = None):
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

        if self._requires_update_key(schema_file_path):
            uk = schema.get("update_key")
            if not isinstance(uk, str) or not uk.strip():
                loc = f" ({schema_file_path})" if schema_file_path else ""
                raise ValueError(
                    f"core/tables 下的 schema 缺少非空字符串字段 update_key{loc}，表名: {schema.get('name')!r}"
                )
        
        # 验证字段定义（使用 Field 对象进行验证）
        for field_dict in schema['fields']:
            if 'name' not in field_dict or 'type' not in field_dict:
                raise ValueError(f"字段定义缺少 name 或 type: {field_dict}")
            
            # 使用 Field.from_dict() 进行验证（会抛出异常如果定义无效）
            try:
                Field.from_dict(field_dict)
            except ValueError as e:
                raise ValueError(f"字段 '{field_dict.get('name', 'unknown')}' 定义无效: {e}")

        self._normalize_storage_domain(schema)
    
    def _normalize_storage_domain(self, schema: Dict) -> None:
        """校验 schema 必须包含 storage_domain。"""
        table_name = str(schema.get("name") or "")
        schema["storage_domain"] = normalize_storage_domain(
            schema.get("storage_domain"), table_name=table_name
        )
    
    def quote_ddl_identifier(self, name: str) -> str:
        """为当前方言引用 DDL 标识符（委托 engine schema_parser）。"""
        return self._ddl_parser().quote_identifier(name)

    # ==================== SQL 生成（委托各 engine schema_parser）====================

    def generate_create_table_sql(self, schema: Dict) -> str:
        """根据 schema 生成 CREATE TABLE SQL。"""
        return self._ddl_parser().generate_create_table_sql(schema)

    def generate_create_index_sql(self, table_name: str, index: Dict) -> str:
        """生成创建索引的 SQL。"""
        return self._ddl_parser().generate_create_index_sql(table_name, index)

    def generate_add_column_sql(self, table_name: str, field_dict: Dict[str, Any]) -> str:
        """为已存在表生成 ADD COLUMN SQL。"""
        return self._ddl_parser().generate_add_column_sql(table_name, field_dict)

    def _fetch_existing_column_names(
        self, table_name: str, get_connection_func: Callable
    ) -> Set[str]:
        """从 information_schema 读取表上已有列名（方言由 ddl_database_type 决定）。"""
        with get_connection_func() as conn:
            return fetch_column_names(self.ddl_database_type, table_name, conn)

    def sync_missing_columns(
        self, schema: Dict, get_connection_func: Callable
    ) -> List[str]:
        """
        将 schema 中定义但库里缺失的列补齐（CREATE TABLE IF NOT EXISTS 不会自动加列）。
        """
        table_name = schema.get("name")
        if not table_name:
            return []

        try:
            existing = self._fetch_existing_column_names(table_name, get_connection_func)
        except Exception as e:
            logger.debug("跳过列同步（无法读取表结构）%s: %s", table_name, e)
            return []

        if not existing:
            return []

        added: List[str] = []
        for field_dict in schema.get("fields", []):
            col = field_dict.get("name")
            if not col or col in existing:
                continue
            try:
                alter_sql = self.generate_add_column_sql(table_name, field_dict)
                with get_connection_func() as conn:
                    execute_ddl(conn, alter_sql)
                added.append(str(col))
                logger.info("✅ 表 '%s' 已补齐列: %s", table_name, col)
            except Exception as e:
                logger.error("❌ 表 '%s' 补齐列 '%s' 失败: %s", table_name, col, e)
        return added
    
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
        
        with get_connection_func() as conn:
            execute_ddl(conn, create_sql)
        
        logger.debug(f"✅ 表 '{table_name}' 创建成功")

        # 旧库仅有早期 CREATE TABLE：先补列再建索引
        self.sync_missing_columns(schema, get_connection_func)
        
        # 创建索引
        indexes = schema.get('indexes', [])
        if indexes:
            self.create_indexes(table_name, indexes, get_connection_func, schema=schema)
    
    def create_indexes(
        self,
        table_name: str,
        indexes: List[Dict],
        get_connection_func: Callable,
        *,
        schema: Optional[Dict] = None,
    ):
        """
        创建索引
        
        Args:
            table_name: 表名
            indexes: 索引定义列表
            get_connection_func: 获取数据库连接的函数（上下文管理器）
            schema: 可选，用于校验索引列是否已存在
        """
        existing_cols: Optional[Set[str]] = None
        if schema is not None:
            try:
                existing_cols = self._fetch_existing_column_names(
                    table_name, get_connection_func
                )
            except Exception:
                existing_cols = None

        for index in indexes:
            index_fields = index.get("fields") or []
            if existing_cols is not None:
                missing = [f for f in index_fields if f not in existing_cols]
                if missing:
                    logger.warning(
                        "⏭️  跳过索引 '%s'：列 %s 不存在于表 '%s'（请先 sync 列或跑 migrate）",
                        index.get("name"),
                        missing,
                        table_name,
                    )
                    continue
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
