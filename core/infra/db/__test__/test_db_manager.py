"""
DatabaseManager 单元测试
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from core.infra.db import DatabaseManager


def _minimal_mysql_config():
    return {
        "database_type": "mysql",
        "mysql": {
            "host": "localhost",
            "port": 3306,
            "database": "test_db",
            "user": "u",
            "password": "p",
        },
    }


class TestDatabaseManager:
    """DatabaseManager 测试类"""
    
    def test_init_with_config(self):
        """测试使用配置初始化"""
        config = _minimal_mysql_config()
        db = DatabaseManager(config=config, is_verbose=False)
        assert db.config['database_type'] == 'mysql'
        assert db.is_verbose is False
    
    def test_init_without_config(self):
        """测试使用默认配置初始化"""
        with patch('core.infra.db.db_manager.ConfigManager.load_database_config') as mock_config:
            mock_config.return_value = _minimal_mysql_config()
            db = DatabaseManager(is_verbose=False)
            assert db.config['database_type'] == 'mysql'
    
    def test_set_default(self):
        """测试设置默认实例"""
        config = _minimal_mysql_config()
        db = DatabaseManager(config=config, is_verbose=False)
        DatabaseManager.set_default(db)
        assert DatabaseManager.get_default(auto_init=False) == db
        DatabaseManager.reset_default()
    
    def test_get_default_auto_init(self):
        """测试自动初始化默认实例"""
        DatabaseManager.reset_default()
        with patch(
            "core.infra.db.db_manager.ConfigManager.load_database_config",
            return_value=_minimal_mysql_config(),
        ), patch(
            "core.infra.db.engines.mysql.connector.MysqlConnector.connect"
        ):
            db = DatabaseManager.get_default()
            assert db is not None
            assert db.engine is not None
            assert db.uses_engine_path
            assert db.table_manager is None
            DatabaseManager.reset_default()
    
    def test_reset_default(self):
        """测试重置默认实例"""
        config = _minimal_mysql_config()
        db = DatabaseManager(config=config, is_verbose=False)
        DatabaseManager.set_default(db)
        DatabaseManager.reset_default()
        assert DatabaseManager._default_instance is None
    
    def test_initialize(self):
        """测试初始化数据库管理器（MySQL Engine 路径）"""
        config = _minimal_mysql_config()
        db = DatabaseManager(config=config, is_verbose=False)

        with patch("core.infra.db.engines.mysql.connector.MysqlConnector.connect"):
            db.initialize()
            assert db._initialized is True
            assert db.uses_engine_path
            assert db.engine is not None
            assert db.engine.is_initialized is True
            assert db.table_manager is None
            assert db.adapter is db.engine.adapter
    
    def test_execute_sync_query(self):
        """测试执行同步查询"""
        config = _minimal_mysql_config()
        db = DatabaseManager(config=config, is_verbose=False)

        with patch("core.infra.db.engines.mysql.connector.MysqlConnector.connect"):
            db.initialize()

        db.engine.execute_sync_query = Mock(return_value=[{"id": "001", "name": "test"}])

        results = db.execute_sync_query(
            "SELECT * FROM test_table WHERE id = %s", ("001",)
        )
        assert results == [{"id": "001", "name": "test"}]
        db.engine.execute_sync_query.assert_called_once()
    
    def test_get_stats(self):
        """测试获取统计信息"""
        config = {
            "database_type": "postgresql",
            "postgresql": {
                "host": "localhost",
                "port": 5432,
                "database": "test_db",
                "user": "test_user",
                "password": "test_pass",
            },
        }
        db = DatabaseManager(config=config, is_verbose=False)
        with patch("core.infra.db.engines.pgsql.connector.PgsqlConnector.connect"):
            db.initialize()

        stats = db.get_stats()
        assert stats["initialized"] is True
        assert stats["engine_key"] == "postgresql"
        assert stats["database"] == "test_db"
        assert stats["host"] == "localhost"
    
    def test_close(self):
        """测试关闭数据库连接"""
        config = _minimal_mysql_config()
        db = DatabaseManager(config=config, is_verbose=False)

        with patch("core.infra.db.engines.mysql.connector.MysqlConnector.connect"):
            db.initialize()

        mock_engine_close = Mock()
        db.engine.close = mock_engine_close
        db._initialized = True

        db.close()
        mock_engine_close.assert_called_once()
        assert db.engine is None
        assert db._initialized is False
