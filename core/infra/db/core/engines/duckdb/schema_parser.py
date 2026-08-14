"""DuckDB schema → DDL。"""
from core.infra.db.core.engines.shared.schema_parser_base import SchemaParserBase


class DuckdbSchemaParser(SchemaParserBase):
    dialect = "duckdb"
