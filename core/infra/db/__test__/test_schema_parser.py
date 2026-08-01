"""Per-engine schema_parser 与 SchemaManager 委托一致性。"""
from core.infra.db.core.engines.duckdb.schema_parser import DuckdbSchemaParser
from core.infra.db.core.engines.mysql.schema_parser import MysqlSchemaParser
from core.infra.db.core.engines.schema_parser_factory import get_schema_parser
from core.infra.db.core.schema_manager import SchemaManager


def test_factory_returns_dialect_parser():
    assert isinstance(get_schema_parser("mysql"), MysqlSchemaParser)
    assert isinstance(get_schema_parser("duckdb"), DuckdbSchemaParser)


def test_schema_manager_delegates_duckdb_create_table():
    schema = {
        "name": "sys_areas",
        "primaryKey": "id",
        "fields": [
            {"name": "id", "type": "int", "autoIncrement": True, "nullable": False},
        ],
    }
    via_manager = SchemaManager(database_type="duckdb").generate_create_table_sql(schema)
    via_parser = DuckdbSchemaParser().generate_create_table_sql(schema)
    assert via_manager == via_parser
    assert "nextval('seq_sys_areas_id')" in via_parser
