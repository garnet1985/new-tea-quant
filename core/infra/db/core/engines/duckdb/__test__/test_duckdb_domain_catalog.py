"""DuckdbDomainCatalog — 动态 schema → 表文件映射。"""
import pytest

from core.infra.db.core.engines.duckdb.domain_catalog import DuckdbDomainCatalog
from core.infra.db.core.engines.duckdb.settings import DuckdbSettings


def _settings():
    return DuckdbSettings.from_dict(
        {
            "domains": {
                "data": {"db_path": "data.duckdb"},
                "tag": {"db_path": "tag.duckdb"},
                "strategy": {"db_path": "strategy.duckdb"},
            },
        }
    )


def test_from_schemas_builds_table_file_map():
    schemas = {
        "sys_stock_list": {
            "name": "sys_stock_list",
            "storage_domain": "data",
            "fields": [],
        },
        "sys_tag_value": {
            "name": "sys_tag_value",
            "storage_domain": "tag",
            "fields": [],
        },
    }
    catalog = DuckdbDomainCatalog.from_schemas(_settings(), schemas)
    fm = catalog.file_map_for_table("sys_tag_value")
    assert fm.domain == "tag"
    assert fm.db_path == "tag.duckdb"
    assert fm.absolute_path.endswith("tag.duckdb")
    assert catalog.resolve_domain("sys_stock_list") == "data"


def test_unknown_table_raises():
    catalog = DuckdbDomainCatalog.from_schemas(
        _settings(),
        {"t": {"name": "t", "storage_domain": "data", "fields": []}},
    )
    with pytest.raises(KeyError, match="未在 DuckDB 文件映射"):
        catalog.file_map_for_table("missing_table")
