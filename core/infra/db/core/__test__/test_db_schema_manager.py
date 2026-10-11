"""
SchemaManager 单元测试
"""
import pytest
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch
from core.infra.db.core.schema_manager import SchemaManager


class TestSchemaManager:
    """SchemaManager 测试类"""
    
    def test_init_default(self):
        """测试默认初始化"""
        manager = SchemaManager(is_verbose=False)
        assert manager.is_verbose is False
        assert manager.database_type == 'postgresql'
        assert manager.registered_tables == {}
    
    def test_init_with_params(self):
        """测试使用参数初始化"""
        manager = SchemaManager(
            tables_dir='/tmp/test',
            is_verbose=True,
            database_type='mysql'
        )
        assert manager.tables_dir == '/tmp/test'
        assert manager.is_verbose is True
        assert manager.database_type == 'mysql'
    
    def test_kind_must_match_table_name(self):
        """kind 必填，且必须等于表名第二段。"""
        manager = SchemaManager(is_verbose=False)
        base = {
            "storage_domain": "data",
            "fields": [{"name": "id", "type": "varchar", "length": 8, "nullable": False}],
        }
        with pytest.raises(ValueError, match="缺少 kind"):
            manager._validate_schema({**base, "name": "sys_data_demo"})
        with pytest.raises(ValueError, match="不一致"):
            manager._validate_schema({**base, "kind": "map", "name": "sys_data_demo"})
        manager._validate_schema({**base, "kind": "data", "name": "sys_data_demo"})
        manager._validate_schema({**base, "kind": "data", "name": "cust_data_demo"})

    def test_load_schema_from_file(self):
        """测试从文件加载 schema"""
        # 创建临时 schema 文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            schema_data = {
                'kind': 'data',
                'name': 'sys_data_test_table',
                'storage_domain': 'data',
                'fields': [
                    {'name': 'id', 'type': 'VARCHAR', 'length': 50, 'primary_key': True},
                    {'name': 'name', 'type': 'VARCHAR', 'length': 100}
                ]
            }
            json.dump(schema_data, f)
            schema_file = f.name
        
        try:
            manager = SchemaManager(is_verbose=False)
            schema = manager.load_schema_from_file(schema_file)
            assert 'fields' in schema
            assert isinstance(schema['fields'], list)
            field_names = [f['name'] for f in schema['fields']]
            assert 'id' in field_names
        finally:
            os.unlink(schema_file)
    
    def test_register_table(self):
        """测试注册表"""
        manager = SchemaManager(is_verbose=False)
        schema = {
            'fields': {
                'id': {'type': 'string', 'primary_key': True}
            }
        }
        manager.register_table('test_table', schema)
        assert 'test_table' in manager.registered_tables
        assert manager.registered_tables['test_table'] == schema
    
    def test_get_table_schema(self):
        """测试获取表 schema"""
        manager = SchemaManager(is_verbose=False)
        schema = {
            'fields': {
                'id': {'type': 'string', 'primary_key': True}
            }
        }
        manager.register_table('test_table', schema)
        result = manager.get_table_schema('test_table')
        assert result == schema
    
    def test_get_table_schema_not_found(self):
        """测试获取不存在的表 schema"""
        manager = SchemaManager(is_verbose=False)
        result = manager.get_table_schema('non_existent_table')
        assert result is None
    
    def test_generate_create_table_sql_duckdb_auto_increment(self):
        """DuckDB 自增列使用 SEQUENCE + nextval，不用 SERIAL/BIGSERIAL。"""
        manager = SchemaManager(is_verbose=False, database_type="duckdb")
        schema = {
            "name": "sys_data_areas",
            "primaryKey": "id",
            "fields": [
                {
                    "name": "id",
                    "type": "int",
                    "autoIncrement": True,
                    "nullable": False,
                },
                {"name": "value", "type": "varchar", "length": 64},
            ],
        }
        sql = manager.generate_create_table_sql(schema)
        assert "SERIAL" not in sql
        assert "seq_sys_data_areas_id" in sql
        assert "nextval('seq_sys_data_areas_id')" in sql

        schema_big = {
            "name": "sys_data_tag_definition",
            "primaryKey": "id",
            "fields": [
                {
                    "name": "id",
                    "type": "bigint",
                    "autoIncrement": True,
                    "nullable": False,
                },
            ],
        }
        sql_big = manager.generate_create_table_sql(schema_big)
        assert "BIGSERIAL" not in sql_big
        assert "BIGINT" in sql_big

    def test_generate_create_table_sql_duckdb_datetime_as_varchar(self):
        """DuckDB 日期/时间列用 VARCHAR 存 YYYYMMDD 与常见时间串。"""
        manager = SchemaManager(is_verbose=False, database_type="duckdb")
        schema = {
            "name": "sys_data_stock_list",
            "primaryKey": "id",
            "fields": [
                {"name": "id", "type": "varchar", "length": 16, "nullable": False},
                {"name": "last_update", "type": "datetime", "nullable": True},
            ],
        }
        sql = manager.generate_create_table_sql(schema)
        assert "TIMESTAMP" not in sql
        assert "VARCHAR(19)" in sql

    def test_get_table_fields(self):
        """测试获取表字段"""
        manager = SchemaManager(is_verbose=False)
        schema = {
            'fields': [
                {'name': 'id', 'type': 'string'},
                {'name': 'name', 'type': 'string'},
                {'name': 'price', 'type': 'float'}
            ]
        }
        manager.register_table('test_table', schema)
        fields = manager.get_table_fields('test_table')
        assert 'id' in fields
        assert 'name' in fields
        assert 'price' in fields
        assert len(fields) == 3
