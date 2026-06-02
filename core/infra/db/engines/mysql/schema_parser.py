"""MySQL schema → DDL。"""
from core.infra.db.engines._shared.schema_parser_base import SchemaParserBase


class MysqlSchemaParser(SchemaParserBase):
    dialect = "mysql"
