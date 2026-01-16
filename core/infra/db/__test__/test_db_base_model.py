"""
DbBaseModel 单元测试
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from core.infra.db.table_queryers.db_base_model import DbBaseModel
from core.infra.db.helpers.db_helpers import DBHelper


class TestDBHelper:
    """DBHelper 测试类"""
    
    def test_to_columns_and_values(self):
        """测试转换为列名和占位符"""
        data_list = [
            {'id': '001', 'name': 'test', 'price': 10.0}
        ]
        columns, placeholders = DBHelper.to_columns_and_values(data_list)
        assert columns == ['id', 'name', 'price']
        assert placeholders == '%s, %s, %s'
    
    def test_to_columns_and_values_empty(self):
        """测试空数据列表"""
        columns, placeholders = DBHelper.to_columns_and_values([])
        assert columns == []
        assert placeholders == ""
    
    def test_to_upsert_params(self):
        """测试转换为 upsert 参数"""
        data_list = [
            {'id': '001', 'name': 'test', 'price': 10.0}
        ]
        columns, values, update_clause = DBHelper.to_upsert_params(
            data_list, 
            unique_keys=['id']
        )
        assert columns == ['id', 'name', 'price']
        assert values == [('001', 'test', 10.0)]
        assert 'name = EXCLUDED.name' in update_clause
        assert 'price = EXCLUDED.price' in update_clause


class TestDbBaseModel:
    """DbBaseModel 测试类"""
    
    def test_init_with_db(self):
        """测试使用传入的 db 初始化"""
        mock_db = Mock()
        model = DbBaseModel('test_table', db=mock_db)
        assert model.db == mock_db
        assert model.table_name == 'test_table'
    
    def test_init_without_db(self):
        """测试使用默认 db 初始化"""
        with patch('core.infra.db.table_queryers.db_base_model.DatabaseManager.get_default') as mock_get_default:
            mock_db = Mock()
            mock_get_default.return_value = mock_db
            
            model = DbBaseModel('test_table')
            assert model.db == mock_db
            assert model.table_name == 'test_table'
    
    def test_load_schema(self):
        """测试加载 schema"""
        mock_db = Mock()
        with patch('core.infra.db.table_queryers.db_base_model.Path') as mock_path:
            mock_schema_file = Mock()
            mock_schema_file.exists.return_value = True
            mock_schema_file.read_text.return_value = '{"fields": {"id": {"type": "string"}}}'
            mock_path.return_value = mock_schema_file
            
            model = DbBaseModel('test_table', db=mock_db)
            # schema 应该被加载
            assert hasattr(model, 'schema')
    
    def test_load(self):
        """测试加载数据"""
        mock_db = Mock()
        mock_db.execute_sync_query.return_value = [
            {'id': '001', 'name': 'test'}
        ]
        
        model = DbBaseModel('test_table', db=mock_db)
        results = model.load("id = %s", ('001',))
        
        assert results == [{'id': '001', 'name': 'test'}]
        mock_db.execute_sync_query.assert_called_once()
    
    def test_load_one(self):
        """测试加载单条数据"""
        mock_db = Mock()
        mock_db.execute_sync_query.return_value = [
            {'id': '001', 'name': 'test'}
        ]
        
        model = DbBaseModel('test_table', db=mock_db)
        result = model.load_one("id = %s", ('001',))
        
        assert result == {'id': '001', 'name': 'test'}
    
    def test_load_one_empty(self):
        """测试加载单条数据（无结果）"""
        mock_db = Mock()
        mock_db.execute_sync_query.return_value = []
        
        model = DbBaseModel('test_table', db=mock_db)
        result = model.load_one("id = %s", ('001',))
        
        assert result is None
    
    def test_save(self):
        """测试保存单条数据"""
        mock_db = Mock()
        mock_db.queue_write = Mock()
        
        model = DbBaseModel('test_table', db=mock_db)
        model.save({'id': '001', 'name': 'test'})
        
        mock_db.queue_write.assert_called_once()
    
    def test_save_many(self):
        """测试批量保存"""
        mock_db = Mock()
        mock_db.queue_write = Mock()
        
        model = DbBaseModel('test_table', db=mock_db)
        data_list = [
            {'id': '001', 'name': 'test1'},
            {'id': '002', 'name': 'test2'}
        ]
        model.save_many(data_list)
        
        mock_db.queue_write.assert_called_once()
