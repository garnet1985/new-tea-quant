"""DuckDB Engine 包（实现细节；公开能力走 ``Db.duckdb_*`` 门面命名空间）。"""

from core.infra.db.core.engines.duckdb.domain_catalog import (
    DuckdbDomainCatalog,
    DuckdbTableFileMap,
)
from core.infra.db.core.engines.duckdb.engine import DuckdbEngine
from core.infra.db.core.engines.duckdb.table_operator import DuckdbTableOperator

__all__ = [
    "DuckdbEngine",
    "DuckdbTableOperator",
    "DuckdbDomainCatalog",
    "DuckdbTableFileMap",
]
