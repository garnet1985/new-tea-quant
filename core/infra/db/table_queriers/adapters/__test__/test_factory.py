"""
DatabaseAdapterFactory 单元测试
"""
import pytest
from unittest.mock import Mock, patch
from core.infra.db.table_queriers.adapters.factory import DatabaseAdapterFactory


class TestDatabaseAdapterFactory:
    """DatabaseAdapterFactory 测试类"""
    
    def test_create_postgresql(self):
        """测试创建 PostgreSQL 适配器"""
        config = {
            'database_type': 'postgresql',
            'postgresql': {
                'host': 'localhost',
                'port': 5432,
                'database': 'test_db',
                'user': 'test_user',
                'password': 'test_pass'
            }
        }
        
        with patch('core.infra.db.table_queriers.adapters.factory.PostgreSQLAdapter') as mock_adapter_class:
            mock_adapter = Mock()
            mock_adapter_class.return_value = mock_adapter
            
            adapter = DatabaseAdapterFactory.create(config, is_verbose=False)
            mock_adapter_class.assert_called_once()
            mock_adapter.connect.assert_called_once()
    
    def test_create_mysql(self):
        """测试创建 MySQL 适配器"""
        config = {
            'database_type': 'mysql',
            'mysql': {
                'host': 'localhost',
                'port': 3306,
                'database': 'test_db',
                'user': 'test_user',
                'password': 'test_pass'
            }
        }
        
        with patch('core.infra.db.table_queriers.adapters.factory.MySQLAdapter') as mock_adapter_class:
            mock_adapter = Mock()
            mock_adapter_class.return_value = mock_adapter
            
            adapter = DatabaseAdapterFactory.create(config, is_verbose=False)
            mock_adapter_class.assert_called_once()
            mock_adapter.connect.assert_called_once()
    
    def test_create_sqlite(self):
        """测试创建 SQLite 适配器"""
        config = {
            'database_type': 'sqlite',
            'sqlite': {
                'db_path': ':memory:'
            }
        }
        
        with patch('core.infra.db.table_queriers.adapters.factory.SQLiteAdapter') as mock_adapter_class:
            mock_adapter = Mock()
            mock_adapter_class.return_value = mock_adapter
            
            adapter = DatabaseAdapterFactory.create(config, is_verbose=False)
            mock_adapter_class.assert_called_once()
            mock_adapter.connect.assert_called_once()
    
    def test_create_invalid_type(self):
        """测试创建无效的数据库类型"""
        config = {
            'database_type': 'invalid_db'
        }
        
        with pytest.raises(ValueError, match="不支持的数据库类型"):
            DatabaseAdapterFactory.create(config)
