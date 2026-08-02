"""PostgreSQL schema → DDL。"""
from core.infra.db.core.engines.shared.schema_parser_base import SchemaParserBase


class PgsqlSchemaParser(SchemaParserBase):
    dialect = "postgresql"
