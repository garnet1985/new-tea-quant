"""PostgreSQL schema → DDL。"""
from core.infra.db.engines._shared.schema_parser_base import SchemaParserBase


class PgsqlSchemaParser(SchemaParserBase):
    dialect = "postgresql"
