"""StorageRegistry 与 DuckDB 配置解析测试。"""
import pytest

from core.infra.db.storage_registry import StorageRegistry, normalize_storage_domain
from core.infra.db.helpers.db_helpers import DBHelper


class TestStorageRegistry:
    def test_register_schema_requires_domain(self):
        reg = StorageRegistry("duckdb")
        with pytest.raises(ValueError, match="storage_domain"):
            reg.register_schema({"name": "sys_x", "fields": []})
        reg.register_schema(
            {"name": "sys_x", "storage_domain": "data", "fields": []}
        )
        assert reg.get_domain("sys_x") == "data"

    def test_register_conflict(self):
        reg = StorageRegistry("duckdb")
        reg.register_table("sys_a", "data")
        with pytest.raises(ValueError, match="冲突"):
            reg.register_table("sys_a", "tag")

    def test_get_domain_unregistered(self):
        reg = StorageRegistry("duckdb")
        with pytest.raises(KeyError):
            reg.get_domain("sys_missing")

    def test_parse_duckdb_config(self):
        cfg = DBHelper.parse_database_config(
            {
                "database_type": "duckdb",
                "duckdb": {
                    "domains": {
                        "data": {"db_path": "data/data.duckdb"},
                        "tag": {"db_path": "data/tag.duckdb"},
                        "strategy": {"db_path": "data/strategy.duckdb"},
                    }
                },
            }
        )
        assert cfg["database_type"] == "duckdb"
        assert "data" in cfg["duckdb"]["domains"]

    def test_normalize_storage_domain_invalid(self):
        with pytest.raises(ValueError):
            normalize_storage_domain("invalid", table_name="t")
