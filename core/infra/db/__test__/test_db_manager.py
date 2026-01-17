"""
DatabaseManager 单元测试
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from core.infra.db import DatabaseManager


class TestDatabaseManager:
    """DatabaseManager 测试类"""
    
    def test_init_with_config(self):
        """测试使用配置初始化"""
        config = {
            'database_type': 'sqlite',
            'sqlite': {'db_path': ':memory:'}
        }
        db = DatabaseManager(config=config, is_verbose=False)
        assert db.config['database_type'] == 'sqlite'
        assert db.is_verbose is False
    
    def test_init_without_config(self):
        """测试使用默认配置初始化"""
        with patch('core.infra.db.db_manager.ConfigManager.get_database_config') as mock_config:
            mock_config.return_value = {
                'database_type': 'sqlite',
                'sqlite': {'db_path': ':memory:'}
            }
            db = DatabaseManager(is_verbose=False)
            assert db.config['database_type'] == 'sqlite'
    
    def test_set_default(self):
        """测试设置默认实例"""
        config = {
            'database_type': 'sqlite',
            'sqlite': {'db_path': ':memory:'}
        }
        db = DatabaseManager(config=config, is_verbose=False)
        DatabaseManager.set_default(db)
        assert DatabaseManager.get_default(auto_init=False) == db
        DatabaseManager.reset_default()
    
    def test_get_default_auto_init(self):
        """测试自动初始化默认实例"""
        DatabaseManager.reset_default()
        with patch('core.infra.db.table_queriers.adapters.factory.DatabaseAdapterFactory.create') as mock_factory:
            mock_adapter = Mock()
            mock_factory.return_value = mock_adapter
            
            db = DatabaseManager.get_default()
            assert db is not None
            DatabaseManager.reset_default()
    
    def test_reset_default(self):
        """测试重置默认实例"""
        config = {
            'database_type': 'sqlite',
            'sqlite': {'db_path': ':memory:'}
        }
        db = DatabaseManager(config=config, is_verbose=False)
        DatabaseManager.set_default(db)
        DatabaseManager.reset_default()
        assert DatabaseManager._default_instance is None
    
    def test_initialize(self):
        """测试初始化数据库管理器"""
        config = {
            'database_type': 'sqlite',
            'sqlite': {'db_path': ':memory:'}
        }
        db = DatabaseManager(config=config, is_verbose=False)
        
        with patch('core.infra.db.table_queriers.adapters.factory.DatabaseAdapterFactory.create') as mock_factory:
            mock_adapter = Mock()
            mock_factory.return_value = mock_adapter
            
            db.initialize()
            assert db._initialized is True
            assert db.adapter == mock_adapter
    
    def test_execute_sync_query(self):
        """测试执行同步查询"""
        config = {
            'database_type': 'sqlite',
            'sqlite': {'db_path': ':memory:'}
        }
        db = DatabaseManager(config=config, is_verbose=False)
        
        mock_adapter = Mock()
        mock_adapter.execute_query.return_value = [{'id': '001', 'name': 'test'}]
        db.adapter = mock_adapter
        db._initialized = True
        
        results = db.execute_sync_query("SELECT * FROM table WHERE id = %s", ('001',))
        assert results == [{'id': '001', 'name': 'test'}]
        mock_adapter.execute_query.assert_called_once_with("SELECT * FROM table WHERE id = %s", ('001',))
    
    def test_get_stats(self):
        """测试获取统计信息"""
        config = {
            'database_type': 'postgresql',
            'postgresql': {
                'host': 'localhost',
                'port': 5432,
                'database': 'test_db'
            }
        }
        db = DatabaseManager(config=config, is_verbose=False)
        db._initialized = True
        
        stats = db.get_stats()
        assert stats['initialized'] is True
        assert stats['database_type'] == 'postgresql'
        assert stats['host'] == 'localhost'
        assert stats['port'] == 5432
        assert stats['database'] == 'test_db'
    
    def test_close(self):
        """测试关闭数据库连接"""
        config = {
            'database_type': 'sqlite',
            'sqlite': {'db_path': ':memory:'}
        }
        db = DatabaseManager(config=config, is_verbose=False)
        
        mock_adapter = Mock()
        db.adapter = mock_adapter
        db._initialized = True
        
        db.close()
        mock_adapter.close.assert_called_once()
        assert db.adapter is None
        assert db._initialized is False
