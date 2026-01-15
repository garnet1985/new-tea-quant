#!/usr/bin/env python3
"""
DuckDB 到 PostgreSQL 数据迁移脚本

功能：
1. 从 DuckDB 读取所有表和数据
2. 在 PostgreSQL 中创建对应的表结构
3. 批量迁移数据
4. 验证数据完整性
"""
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
from loguru import logger
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import duckdb
    import psycopg2
    from psycopg2.extras import RealDictCursor, execute_batch
except ImportError as e:
    logger.error(f"❌ 缺少依赖: {e}")
    logger.info("请运行: pip install psycopg2-binary duckdb")
    sys.exit(1)

from core.infra.db.db_schema_manager import DbSchemaManager
from core.config.loaders.db_conf import load_duckdb_conf


class PostgreSQLSchemaAdapter:
    """PostgreSQL Schema 适配器，将 DuckDB schema 转换为 PostgreSQL schema"""
    
    @staticmethod
    def convert_field_type(field: Dict) -> str:
        """转换字段类型为 PostgreSQL 类型"""
        field_type = field['type'].upper()
        is_auto_increment = field.get('autoIncrement', False) or field.get('isAutoIncrement', False)
        
        # 类型映射
        if field_type == 'VARCHAR' and 'length' in field:
            return f"VARCHAR({field['length']})"
        elif field_type == 'TEXT':
            return "TEXT"
        elif field_type == 'TINYINT' and 'length' in field and field.get('length') == 1:
            return "BOOLEAN"
        elif field_type == 'TINYINT':
            return "INTEGER"
        elif field_type == 'INT' or field_type == 'INTEGER':
            if is_auto_increment:
                return "SERIAL"
            return "INTEGER"
        elif field_type == 'BIGINT':
            if is_auto_increment:
                return "BIGSERIAL"
            return "BIGINT"
        elif field_type == 'FLOAT' or field_type == 'DOUBLE':
            return "DOUBLE PRECISION"
        elif field_type == 'DECIMAL' or field_type == 'NUMERIC':
            # 处理 DECIMAL(10,2) 格式
            if 'length' in field:
                length = field['length']
                if isinstance(length, str):
                    # 如果是字符串 "10,2"，直接使用
                    return f"DECIMAL({length})"
                elif isinstance(length, (int, float)):
                    return f"DECIMAL({length})"
            return "DECIMAL"
        elif field_type == 'DATETIME':
            return "TIMESTAMP"
        elif field_type == 'DATE':
            return "DATE"
        elif field_type == 'JSON':
            return "JSONB"  # PostgreSQL 使用 JSONB 更高效
        else:
            return field_type
    
    @staticmethod
    def generate_create_table_sql(schema: Dict) -> str:
        """生成 PostgreSQL CREATE TABLE SQL"""
        table_name = schema['name']
        fields = schema['fields']
        primary_key = schema.get('primaryKey')
        
        field_defs = []
        for field in fields:
            field_name = field['name']
            field_type = PostgreSQLSchemaAdapter.convert_field_type(field)
            is_required = field.get('isRequired', False)
            default_value = field.get('default')
            
            field_def = f"{field_name} {field_type}"
            
            if is_required:
                field_def += " NOT NULL"
            
            if default_value is not None:
                # 处理 MySQL 的 ON UPDATE CURRENT_TIMESTAMP 语法
                # PostgreSQL 不支持 ON UPDATE，只保留 CURRENT_TIMESTAMP
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
                        field_type_upper = field['type'].upper()
                        # 处理 BOOLEAN 类型的默认值
                        if field_type_upper == 'TINYINT' and 'length' in field and field.get('length') == 1:
                            # TINYINT(1) 转换为 BOOLEAN，需要转换默认值
                            if default_value in ['0', 0, 'false', 'FALSE']:
                                field_def += " DEFAULT FALSE"
                            elif default_value in ['1', 1, 'true', 'TRUE']:
                                field_def += " DEFAULT TRUE"
                            else:
                                field_def += f" DEFAULT {default_value}"
                        elif field_type_upper in ['VARCHAR', 'TEXT', 'CHAR', 'DATE', 'DATETIME', 'TIME', 'TIMESTAMP']:
                            field_def += f" DEFAULT '{default_value}'"
                        else:
                            field_def += f" DEFAULT {default_value}"
                else:
                    # 非字符串默认值
                    field_type_upper = field['type'].upper()
                    # 处理 BOOLEAN 类型的默认值
                    if field_type_upper == 'TINYINT' and 'length' in field and field.get('length') == 1:
                        # TINYINT(1) 转换为 BOOLEAN，需要转换默认值
                        if default_value in [0, '0', False, 'false', 'FALSE']:
                            field_def += " DEFAULT FALSE"
                        elif default_value in [1, '1', True, 'true', 'TRUE']:
                            field_def += " DEFAULT TRUE"
                        else:
                            field_def += f" DEFAULT {default_value}"
                    elif field_type_upper in ['VARCHAR', 'TEXT', 'CHAR', 'DATE', 'DATETIME', 'TIME', 'TIMESTAMP']:
                        field_def += f" DEFAULT '{default_value}'"
                    else:
                        field_def += f" DEFAULT {default_value}"
            
            field_defs.append(field_def)
        
        # 添加主键（PostgreSQL 在字段定义后添加）
        if primary_key:
            if isinstance(primary_key, list):
                pk_fields = ', '.join(primary_key)
                field_defs.append(f"PRIMARY KEY ({pk_fields})")
            else:
                field_defs.append(f"PRIMARY KEY ({primary_key})")
        
        fields_sql = ',\n    '.join(field_defs)
        create_sql = f"""
CREATE TABLE IF NOT EXISTS {table_name} (
    {fields_sql}
);
        """.strip()
        
        return create_sql
    
    @staticmethod
    def generate_create_index_sql(table_name: str, index: Dict) -> str:
        """生成 PostgreSQL CREATE INDEX SQL"""
        index_name = index['name']
        index_fields = index['fields']
        is_unique = index.get('unique', False)
        
        unique_keyword = 'UNIQUE' if is_unique else ''
        fields_str = ', '.join(index_fields)
        
        sql = f"CREATE {unique_keyword} INDEX IF NOT EXISTS {index_name} ON {table_name} ({fields_str})"
        return sql


class DataMigrator:
    """数据迁移器"""
    
    def __init__(self, duckdb_path: str, pg_config: Dict, batch_size: int = 10000, batch_sizes: Dict[str, int] = None):
        self.duckdb_path = duckdb_path
        self.pg_config = pg_config
        self.batch_size = batch_size  # 默认批量大小
        self.batch_sizes = batch_sizes or {}  # 表特定的批量大小
        
        # 连接
        self.duckdb_conn = None
        self.pg_conn = None
        
        # Schema 管理器
        self.schema_manager = DbSchemaManager(is_verbose=True)
    
    def get_batch_size(self, table_name: str) -> int:
        """获取表特定的批量大小"""
        return self.batch_sizes.get(table_name, self.batch_size)
    
    def connect(self):
        """建立数据库连接"""
        logger.info("🔌 正在连接数据库...")
        
        # 连接 DuckDB
        if not Path(self.duckdb_path).exists():
            raise FileNotFoundError(f"DuckDB 数据库文件不存在: {self.duckdb_path}")
        
        self.duckdb_conn = duckdb.connect(self.duckdb_path, read_only=True)
        logger.info(f"✅ DuckDB 连接成功: {self.duckdb_path}")
        
        # 连接 PostgreSQL
        self.pg_conn = psycopg2.connect(
            host=self.pg_config["host"],
            port=self.pg_config["port"],
            database=self.pg_config["database"],
            user=self.pg_config["user"],
            password=self.pg_config["password"]
        )
        logger.info(f"✅ PostgreSQL 连接成功: {self.pg_config['database']}")
    
    def close(self):
        """关闭连接"""
        if self.duckdb_conn:
            self.duckdb_conn.close()
        if self.pg_conn:
            self.pg_conn.close()
    
    def get_duckdb_tables(self) -> List[str]:
        """获取 DuckDB 中的所有表"""
        cursor = self.duckdb_conn.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'main'
            ORDER BY table_name;
        """)
        tables = [row[0] for row in cursor.fetchall()]
        return tables
    
    def table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        with self.pg_conn.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = %s
            """, (table_name,))
            result = cursor.fetchone()
            return result[0] > 0 if result else False
    
    def create_table_in_postgresql(self, schema: Dict):
        """在 PostgreSQL 中创建表"""
        table_name = schema['name']
        
        # 检查表是否已存在
        if self.table_exists(table_name):
            logger.info(f"ℹ️  表 {table_name} 已存在，跳过创建")
            return
        
        # 生成建表 SQL
        create_sql = PostgreSQLSchemaAdapter.generate_create_table_sql(schema)
        
        # 执行建表
        try:
            logger.debug(f"   执行建表 SQL: {create_sql[:200]}...")  # 只显示前200字符
            
            with self.pg_conn.cursor() as cursor:
                cursor.execute(create_sql)
                logger.info(f"✅ 创建表: {table_name}")
            
            # 创建索引
            if 'indexes' in schema:
                with self.pg_conn.cursor() as cursor:
                    for index in schema['indexes']:
                        try:
                            index_sql = PostgreSQLSchemaAdapter.generate_create_index_sql(table_name, index)
                            cursor.execute(index_sql)
                            logger.info(f"   ✅ 创建索引: {index['name']}")
                        except Exception as e:
                            logger.warning(f"   ⚠️  创建索引失败 {index['name']}: {e}")
                            # 索引创建失败不影响表创建，继续
            
            self.pg_conn.commit()
            
            # 验证表是否创建成功
            if not self.table_exists(table_name):
                error_msg = f"表 {table_name} 创建后验证失败，表不存在"
                logger.error(f"❌ {error_msg}")
                logger.error(f"   建表 SQL:\n{create_sql}")
                raise RuntimeError(error_msg)
            else:
                logger.debug(f"   ✅ 表 {table_name} 验证通过")
                
        except psycopg2.Error as e:
            self.pg_conn.rollback()
            error_msg = f"创建表失败 {table_name}: {e}"
            logger.error(f"❌ {error_msg}")
            logger.error(f"   建表 SQL:\n{create_sql}")
            raise RuntimeError(error_msg) from e
        except Exception as e:
            self.pg_conn.rollback()
            error_msg = f"创建表失败 {table_name}: {e}"
            logger.error(f"❌ {error_msg}")
            logger.error(f"   建表 SQL:\n{create_sql}")
            import traceback
            logger.debug(traceback.format_exc())
            raise RuntimeError(error_msg) from e
    
    def migrate_table_data(self, table_name: str) -> Dict[str, Any]:
        """迁移单个表的数据"""
        # 检查表是否存在
        if not self.table_exists(table_name):
            logger.error(f"❌ 表 {table_name} 不存在，请先创建表结构")
            raise RuntimeError(f"表 {table_name} 不存在，无法迁移数据")
        
        # 获取表特定的批量大小
        batch_size = self.get_batch_size(table_name)
        logger.info(f"\n📦 正在迁移表: {table_name} (批量大小: {batch_size:,})")
        
        # 获取表结构
        schema = self.schema_manager.get_table_schema(table_name)
        if not schema:
            logger.warning(f"⚠️  未找到表 {table_name} 的 schema，跳过")
            return {"table": table_name, "rows": 0, "skipped": True}
        
        # 获取字段列表
        fields = [field['name'] for field in schema['fields']]
        fields_str = ', '.join(fields)
        
        # 从 DuckDB 读取数据总数
        count_cursor = self.duckdb_conn.execute(f"SELECT COUNT(*) as count FROM {table_name}")
        total_rows = count_cursor.fetchone()[0]
        
        if total_rows == 0:
            logger.info(f"   ℹ️  表 {table_name} 为空，跳过数据迁移")
            return {"table": table_name, "rows": 0, "skipped": False}
        
        logger.info(f"   📊 总记录数: {total_rows:,}")
        
        # 批量迁移
        migrated_rows = 0
        offset = 0
        
        # 准备插入 SQL（使用 ON CONFLICT 处理重复）
        primary_key = schema.get('primaryKey')
        if primary_key:
            if isinstance(primary_key, list):
                conflict_cols = ', '.join(primary_key)
            else:
                conflict_cols = primary_key
            
            # 生成 UPDATE 子句（更新所有非主键字段）
            update_fields = [f for f in fields if f not in (primary_key if isinstance(primary_key, list) else [primary_key])]
            if update_fields:
                update_clause = ', '.join([f"{f} = EXCLUDED.{f}" for f in update_fields])
                insert_sql = f"""
                    INSERT INTO {table_name} ({fields_str}) 
                    VALUES ({', '.join(['%s'] * len(fields))})
                    ON CONFLICT ({conflict_cols}) DO UPDATE SET {update_clause}
                """
            else:
                insert_sql = f"""
                    INSERT INTO {table_name} ({fields_str}) 
                    VALUES ({', '.join(['%s'] * len(fields))})
                    ON CONFLICT ({conflict_cols}) DO NOTHING
                """
        else:
            insert_sql = f"""
                INSERT INTO {table_name} ({fields_str}) 
                VALUES ({', '.join(['%s'] * len(fields))})
            """
        
        with self.pg_conn.cursor() as pg_cursor:
            while offset < total_rows:
                # 从 DuckDB 读取一批数据
                query = f"SELECT {fields_str} FROM {table_name} LIMIT {batch_size} OFFSET {offset}"
                duckdb_cursor = self.duckdb_conn.execute(query)
                rows = duckdb_cursor.fetchall()
                
                if not rows:
                    break
                
                # 转换为元组列表
                values_list = []
                for row in rows:
                    # DuckDB 可能返回字典或元组
                    if isinstance(row, dict):
                        values = tuple(row[field] for field in fields)
                    else:
                        values = row
                    values_list.append(values)
                
                # 批量插入 PostgreSQL
                try:
                    execute_batch(pg_cursor, insert_sql, values_list)
                    self.pg_conn.commit()
                    
                    migrated_rows += len(values_list)
                    offset += len(values_list)
                    
                    logger.info(f"   ✅ 已迁移: {migrated_rows:,} / {total_rows:,} ({migrated_rows*100//total_rows}%)")
                    
                except Exception as e:
                    logger.error(f"   ❌ 批量插入失败: {e}")
                    self.pg_conn.rollback()
                    raise
        
        # 验证数据
        pg_cursor = self.pg_conn.cursor()
        pg_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        pg_count = pg_cursor.fetchone()[0]
        pg_cursor.close()
        
        if pg_count == total_rows:
            logger.info(f"   ✅ 数据验证通过: {pg_count:,} 条记录")
        else:
            logger.warning(f"   ⚠️  数据数量不一致: DuckDB={total_rows:,}, PostgreSQL={pg_count:,}")
        
        return {
            "table": table_name,
            "rows": migrated_rows,
            "duckdb_count": total_rows,
            "postgresql_count": pg_count,
            "skipped": False
        }
    
    def migrate_all(self, tables: Optional[List[str]] = None, exclude_tables: Optional[List[str]] = None) -> Dict[str, Any]:
        """迁移所有表
        
        Args:
            tables: 要迁移的表列表（None 表示迁移所有表）
            exclude_tables: 要排除的表列表（如 ['stock_kline'] 表示先不迁移 kline）
        """
        logger.info("=" * 60)
        logger.info("开始数据迁移")
        logger.info("=" * 60)
        
        # 获取要迁移的表列表
        if tables is None:
            duckdb_tables = self.get_duckdb_tables()
            # 加载所有 schema
            all_schemas = self.schema_manager.load_all_schemas()
            # 只迁移有 schema 定义的表
            tables = [t for t in duckdb_tables if t in all_schemas]
        
        # 排除指定的表（先迁移小表）
        exclude_tables = exclude_tables or []
        small_tables = [t for t in tables if t not in exclude_tables]
        large_tables = [t for t in tables if t in exclude_tables]
        
        # 重新排序：先小表，后大表
        ordered_tables = small_tables + large_tables
        
        logger.info(f"\n📋 待迁移表 ({len(ordered_tables)} 个):")
        if small_tables:
            logger.info(f"   小表 ({len(small_tables)} 个): {', '.join(small_tables)}")
        if large_tables:
            logger.info(f"   大表 ({len(large_tables)} 个): {', '.join(large_tables)}")
        
        results = []
        
        # 1. 创建所有表结构
        logger.info("\n" + "=" * 60)
        logger.info("步骤 1: 创建表结构")
        logger.info("=" * 60)
        
        created_tables = []
        for table_name in ordered_tables:
            schema = self.schema_manager.get_table_schema(table_name)
            if schema:
                try:
                    self.create_table_in_postgresql(schema)
                    created_tables.append(table_name)
                except Exception as e:
                    logger.error(f"❌ 创建表失败 {table_name}: {e}")
                    import traceback
                    logger.debug(traceback.format_exc())
                    results.append({
                        "table": table_name,
                        "rows": 0,
                        "error": str(e),
                        "skipped": True
                    })
            else:
                logger.warning(f"⚠️  未找到表 {table_name} 的 schema，跳过")
                results.append({
                    "table": table_name,
                    "rows": 0,
                    "skipped": True
                })
        
        logger.info(f"\n✅ 成功创建 {len(created_tables)} 个表")
        
        # 验证所有表都已创建
        missing_tables = []
        for table_name in ordered_tables:
            if table_name in created_tables and not self.table_exists(table_name):
                missing_tables.append(table_name)
        
        if missing_tables:
            logger.error(f"❌ 以下表创建后验证失败: {', '.join(missing_tables)}")
            raise RuntimeError(f"表创建验证失败: {', '.join(missing_tables)}")
        
        # 2. 迁移数据（先小表，后大表）
        # 只迁移成功创建的表
        logger.info("\n" + "=" * 60)
        logger.info("步骤 2: 迁移数据（先小表，后大表）")
        logger.info("=" * 60)
        
        # 过滤出成功创建的小表和大表
        small_tables_to_migrate = [t for t in small_tables if t in created_tables]
        large_tables_to_migrate = [t for t in large_tables if t in created_tables]
        
        if small_tables_to_migrate:
            skipped_small = [t for t in small_tables if t not in created_tables]
            if skipped_small:
                logger.warning(f"⚠️  以下小表创建失败，跳过数据迁移: {', '.join(skipped_small)}")
            
            logger.info(f"\n📦 阶段 1: 迁移小表 ({len(small_tables_to_migrate)} 个)")
            for table_name in small_tables_to_migrate:
                try:
                    result = self.migrate_table_data(table_name)
                    results.append(result)
                except Exception as e:
                    logger.error(f"❌ 迁移表失败 {table_name}: {e}")
                    results.append({
                        "table": table_name,
                        "rows": 0,
                        "error": str(e),
                        "skipped": False
                    })
        
        if large_tables_to_migrate:
            skipped_large = [t for t in large_tables if t not in created_tables]
            if skipped_large:
                logger.warning(f"⚠️  以下大表创建失败，跳过数据迁移: {', '.join(skipped_large)}")
            
            logger.info(f"\n📦 阶段 2: 迁移大表 ({len(large_tables_to_migrate)} 个)")
            for table_name in large_tables_to_migrate:
                try:
                    result = self.migrate_table_data(table_name)
                    results.append(result)
                except Exception as e:
                    logger.error(f"❌ 迁移表失败 {table_name}: {e}")
                    results.append({
                        "table": table_name,
                        "rows": 0,
                        "error": str(e),
                        "skipped": False
                    })
        
        # 3. 生成迁移报告
        logger.info("\n" + "=" * 60)
        logger.info("迁移完成")
        logger.info("=" * 60)
        
        total_rows = sum(r.get("rows", 0) for r in results)
        successful_tables = [r for r in results if not r.get("skipped") and not r.get("error")]
        failed_tables = [r for r in results if r.get("error")]
        skipped_tables = [r for r in results if r.get("skipped") and not r.get("error")]
        
        logger.info(f"\n📊 迁移统计:")
        logger.info(f"   成功: {len(successful_tables)} 个表")
        logger.info(f"   失败: {len(failed_tables)} 个表")
        logger.info(f"   跳过: {len(skipped_tables)} 个表")
        logger.info(f"   总记录数: {total_rows:,}")
        
        if failed_tables:
            logger.warning("\n❌ 失败的表:")
            for r in failed_tables:
                logger.warning(f"   - {r['table']}: {r.get('error', 'Unknown error')}")
        
        return {
            "results": results,
            "total_rows": total_rows,
            "successful_tables": len(successful_tables),
            "failed_tables": len(failed_tables),
            "skipped_tables": len(skipped_tables)
        }


def load_pg_config(config_path: Optional[str] = None) -> Dict:
    """加载 PostgreSQL 配置"""
    if config_path:
        config_file = Path(config_path)
    else:
        config_file = project_root / "config" / "database" / "pg_config.json"
    
    if not config_file.exists():
        raise FileNotFoundError(f"PostgreSQL 配置文件不存在: {config_file}")
    
    with config_file.open("r", encoding="utf-8") as f:
        config = json.load(f)
    
    # 优先使用 postgresql 配置
    pg_config = config.get("postgresql") or config.get("stocks_user")
    
    if not pg_config:
        raise ValueError("配置文件中未找到 postgresql 或 stocks_user 配置")
    
    return pg_config


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="DuckDB 到 PostgreSQL 数据迁移工具")
    parser.add_argument("--duckdb-path", type=str, help="DuckDB 数据库文件路径")
    parser.add_argument("--pg-config", type=str, help="PostgreSQL 配置文件路径（可选）")
    parser.add_argument("--batch-size", type=int, default=10000, help="默认批量插入大小（默认: 10000）")
    parser.add_argument("--kline-batch-size", type=int, default=1000000, help="stock_kline 表的批量大小（默认: 1000000）")
    parser.add_argument("--tables", type=str, nargs="+", help="指定要迁移的表（可选，默认迁移所有表）")
    parser.add_argument("--exclude-tables", type=str, nargs="+", help="要排除的表（会最后迁移，如 --exclude-tables stock_kline）")
    
    args = parser.parse_args()
    
    # 加载配置
    try:
        if args.duckdb_path:
            duckdb_path = args.duckdb_path
        else:
            duckdb_conf = load_duckdb_conf()
            duckdb_path = duckdb_conf['db_path']
        
        pg_config = load_pg_config(args.pg_config)
        
        # 设置表特定的批量大小
        batch_sizes = {}
        if args.kline_batch_size:
            batch_sizes['stock_kline'] = args.kline_batch_size
        
        logger.info("📝 配置信息:")
        logger.info(f"   DuckDB: {duckdb_path}")
        logger.info(f"   PostgreSQL: {pg_config['host']}:{pg_config['port']}/{pg_config['database']}")
        logger.info(f"   默认批量大小: {args.batch_size:,}")
        if batch_sizes:
            logger.info(f"   表特定批量大小:")
            for table, size in batch_sizes.items():
                logger.info(f"      - {table}: {size:,}")
        
    except Exception as e:
        logger.error(f"❌ 加载配置失败: {e}")
        sys.exit(1)
    
    # 执行迁移
    migrator = DataMigrator(
        duckdb_path, 
        pg_config, 
        batch_size=args.batch_size,
        batch_sizes=batch_sizes
    )
    
    try:
        migrator.connect()
        results = migrator.migrate_all(
            tables=args.tables,
            exclude_tables=args.exclude_tables
        )
        
        # 保存迁移报告
        report_file = project_root / "migration_report.json"
        with report_file.open("w", encoding="utf-8") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "duckdb_path": duckdb_path,
                "postgresql_database": pg_config["database"],
                "results": results
            }, f, indent=2, ensure_ascii=False)
        
        logger.info(f"\n📄 迁移报告已保存: {report_file}")
        
    except Exception as e:
        logger.error(f"❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        migrator.close()


if __name__ == "__main__":
    main()
