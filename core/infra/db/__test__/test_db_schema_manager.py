"""
DbSchemaManager 单元测试
"""
import pytest
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch
from core.infra.db.schema_management.db_schema_manager import DbSchemaManager


class TestDbSchemaManager:
    """DbSchemaManager 测试类"""
    
    def test_init_default(self):
        """测试默认初始化"""
        manager = DbSchemaManager(is_verbose=False)
        assert manager.is_verbose is False
        assert manager.database_type == 'postgresql'
        assert manager.registered_tables == {}
    
    def test_init_with_params(self):
        """测试使用参数初始化"""
        manager = DbSchemaManager(
            tables_dir='/tmp/test',
            is_verbose=True,
            database_type='mysql'
        )
        assert manager.tables_dir == '/tmp/test'
        assert manager.is_verbose is True
        assert manager.database_type == 'mysql'
    
    def test_load_schema_from_file(self):
        """测试从文件加载 schema"""
        # 创建临时 schema 文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            schema_data = {
                'fields': {
                    'id': {'type': 'string', 'primary_key': True},
                    'name': {'type': 'string'}
                }
            }
            json.dump(schema_data, f)
            schema_file = f.name
        
        try:
            manager = DbSchemaManager(is_verbose=False)
            schema = manager.load_schema_from_file(schema_file)
            assert 'fields' in schema
            assert 'id' in schema['fields']
        finally:
            os.unlink(schema_file)
    
    def test_register_table(self):
        """测试注册表"""
        manager = DbSchemaManager(is_verbose=False)
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
        manager = DbSchemaManager(is_verbose=False)
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
        manager = DbSchemaManager(is_verbose=False)
        result = manager.get_table_schema('non_existent_table')
        assert result is None
    
    def test_get_table_fields(self):
        """测试获取表字段"""
        manager = DbSchemaManager(is_verbose=False)
        schema = {
            'fields': {
                'id': {'type': 'string'},
                'name': {'type': 'string'},
                'price': {'type': 'float'}
            }
        }
        manager.register_table('test_table', schema)
        fields = manager.get_table_fields('test_table')
        assert 'id' in fields
        assert 'name' in fields
        assert 'price' in fields
        assert len(fields) == 3
