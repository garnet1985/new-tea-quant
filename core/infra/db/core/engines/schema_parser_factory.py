"""按 DDL 方言返回 schema_parser 实例。"""
from __future__ import annotations

from typing import TYPE_CHECKING

from core.infra.db.core.engines.shared.schema_parser_base import SchemaParserBase

if TYPE_CHECKING:
    pass

_PARSERS: dict[str, type[SchemaParserBase]] = {}


def _ensure_registry() -> None:
    if _PARSERS:
        return
    from core.infra.db.core.engines.duckdb.schema_parser import DuckdbSchemaParser
    from core.infra.db.core.engines.mysql.schema_parser import MysqlSchemaParser
    from core.infra.db.core.engines.pgsql.schema_parser import PgsqlSchemaParser

    _PARSERS.update(
        {
            "mysql": MysqlSchemaParser,
            "postgresql": PgsqlSchemaParser,
            "duckdb": DuckdbSchemaParser,
        }
    )


def get_schema_parser(dialect: str) -> SchemaParserBase:
    """``dialect`` 为 mysql | postgresql | duckdb。"""
    _ensure_registry()
    key = str(dialect or "postgresql").strip().lower()
    cls = _PARSERS.get(key)
    if cls is None:
        raise ValueError(f"不支持的 DDL 方言: {dialect!r}")
    return cls()
