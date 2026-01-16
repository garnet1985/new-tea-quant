"""
DBHelper 单元测试
"""
import pytest
from core.infra.db.helpers.db_helpers import DBHelper


class TestDBHelper:
    """DBHelper 测试类"""
    
    def test_parse_database_config_valid_postgresql(self):
        """测试解析有效的 PostgreSQL 配置"""
        config = {
            'database_type': 'postgresql',
            'postgresql': {
                'host': 'localhost',
                'port': 5432,
                'database': 'test_db',
                'user': 'test_user',
                'password': 'test_password'
            },
            'batch_write': {
                'enable': True,
                'batch_size': 1000,
                'flush_interval': 5.0
            }
        }
        
        result = DBHelper.parse_database_config(config)
        assert result['database_type'] == 'postgresql'
        assert 'postgresql' in result
        assert 'batch_write' in result
    
    def test_parse_database_config_valid_sqlite(self):
        """测试解析有效的 SQLite 配置"""
        config = {
            'database_type': 'sqlite',
            'sqlite': {
                'db_path': ':memory:'
            }
        }
        
        result = DBHelper.parse_database_config(config)
        assert result['database_type'] == 'sqlite'
        assert 'sqlite' in result
        assert result['sqlite']['db_path'] == ':memory:'
    
    def test_parse_database_config_missing_database_type(self):
        """测试缺少 database_type 的配置"""
        config = {
            'postgresql': {
                'host': 'localhost',
                'port': 5432,
                'database': 'test_db',
                'user': 'test_user',
                'password': 'test_password'
            }
        }
        
        with pytest.raises(ValueError, match="配置中缺少 'database_type' 字段"):
            DBHelper.parse_database_config(config)
    
    def test_parse_database_config_invalid_type(self):
        """测试无效的数据库类型"""
        config = {
            'database_type': 'invalid_db',
            'invalid_db': {}
        }
        
        with pytest.raises(ValueError, match="不支持的数据库类型"):
            DBHelper.parse_database_config(config)
    
    def test_parse_database_config_missing_db_config(self):
        """测试缺少数据库配置"""
        config = {
            'database_type': 'postgresql'
        }
        
        with pytest.raises(ValueError, match="配置中缺少 'postgresql' 数据库配置"):
            DBHelper.parse_database_config(config)
    
    def test_parse_database_config_missing_required_fields_postgresql(self):
        """测试 PostgreSQL 配置缺少必需字段"""
        config = {
            'database_type': 'postgresql',
            'postgresql': {
                'host': 'localhost',
                'port': 5432
                # 缺少 database, user, password
            }
        }
        
        with pytest.raises(ValueError, match="配置中缺少必需字段"):
            DBHelper.parse_database_config(config)
    
    def test_parse_database_config_missing_required_fields_sqlite(self):
        """测试 SQLite 配置缺少必需字段"""
        config = {
            'database_type': 'sqlite',
            'sqlite': {}
            # 缺少 db_path
        }
        
        with pytest.raises(ValueError, match="SQLite 配置中缺少 'db_path' 字段"):
            DBHelper.parse_database_config(config)
    
    def test_parse_database_config_complete_batch_write(self):
        """测试补足 batch_write 默认配置"""
        config = {
            'database_type': 'sqlite',
            'sqlite': {
                'db_path': ':memory:'
            }
            # 缺少 batch_write
        }
        
        result = DBHelper.parse_database_config(config)
        assert 'batch_write' in result
        assert result['batch_write']['enable'] is True
        assert result['batch_write']['batch_size'] == 1000
        assert result['batch_write']['flush_interval'] == 5.0
    
    def test_parse_database_config_partial_batch_write(self):
        """测试部分 batch_write 配置"""
        config = {
            'database_type': 'sqlite',
            'sqlite': {
                'db_path': ':memory:'
            },
            'batch_write': {
                'enable': False
                # 缺少 batch_size 和 flush_interval
            }
        }
        
        result = DBHelper.parse_database_config(config)
        assert result['batch_write']['enable'] is False
        assert result['batch_write']['batch_size'] == 1000  # 补足默认值
        assert result['batch_write']['flush_interval'] == 5.0  # 补足默认值
    
    def test_parse_database_config_normalize_database_type(self):
        """测试 database_type 标准化为小写"""
        config = {
            'database_type': 'POSTGRESQL',  # 大写
            'postgresql': {
                'host': 'localhost',
                'port': 5432,
                'database': 'test_db',
                'user': 'test_user',
                'password': 'test_password'
            }
        }
        
        result = DBHelper.parse_database_config(config)
        assert result['database_type'] == 'postgresql'  # 转换为小写
