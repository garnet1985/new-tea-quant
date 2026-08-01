"""config_parse.parse_database_config 单元测试。"""
import pytest

pytestmark = pytest.mark.force_run

from core.infra.db.core.engines.shared.config_parse import parse_database_config


class TestParseDatabaseConfig:
    def test_valid_postgresql(self):
        config = {
            "database_type": "postgresql",
            "postgresql": {
                "host": "localhost",
                "port": 5432,
                "database": "test_db",
                "user": "test_user",
                "password": "test_password",
            },
            "batch_write": {
                "enable": True,
                "batch_size": 1000,
                "flush_interval": 5.0,
            },
        }
        result = parse_database_config(config)
        assert result["database_type"] == "postgresql"
        assert "postgresql" in result
        assert "batch_write" in result

    def test_missing_database_type(self):
        config = {
            "postgresql": {
                "host": "localhost",
                "port": 5432,
                "database": "test_db",
                "user": "test_user",
                "password": "test_password",
            }
        }
        with pytest.raises(ValueError, match="配置中缺少 'database_type' 字段"):
            parse_database_config(config)

    def test_invalid_type(self):
        config = {"database_type": "invalid_db", "invalid_db": {}}
        with pytest.raises(ValueError, match="不支持的数据库类型"):
            parse_database_config(config)

    def test_missing_db_config(self):
        config = {"database_type": "postgresql"}
        with pytest.raises(ValueError, match="配置中缺少 'postgresql' 数据库配置"):
            parse_database_config(config)

    def test_missing_required_fields_postgresql(self):
        config = {
            "database_type": "postgresql",
            "postgresql": {"host": "localhost", "port": 5432},
        }
        with pytest.raises(ValueError, match="配置中缺少必需字段"):
            parse_database_config(config)

    def test_complete_batch_write_defaults(self):
        config = {
            "database_type": "mysql",
            "mysql": {
                "host": "localhost",
                "port": 3306,
                "database": "test_db",
                "user": "u",
                "password": "p",
            },
        }
        result = parse_database_config(config)
        assert result["batch_write"]["enable"] is True
        assert result["batch_write"]["batch_size"] == 1000
        assert result["batch_write"]["flush_interval"] == 5.0

    def test_partial_batch_write(self):
        config = {
            "database_type": "mysql",
            "mysql": {
                "host": "localhost",
                "port": 3306,
                "database": "test_db",
                "user": "u",
                "password": "p",
            },
            "batch_write": {"enable": False},
        }
        result = parse_database_config(config)
        assert result["batch_write"]["enable"] is False
        assert result["batch_write"]["batch_size"] == 1000
        assert result["batch_write"]["flush_interval"] == 5.0

    def test_normalize_database_type_lowercase(self):
        config = {
            "database_type": "POSTGRESQL",
            "postgresql": {
                "host": "localhost",
                "port": 5432,
                "database": "test_db",
                "user": "test_user",
                "password": "test_password",
            },
        }
        result = parse_database_config(config)
        assert result["database_type"] == "postgresql"
