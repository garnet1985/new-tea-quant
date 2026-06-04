"""DuckDB Engine 包。"""

from core.infra.db.engines.duckdb.domain_catalog import (
    DuckdbDomainCatalog,
    DuckdbTableFileMap,
)
from core.infra.db.engines.duckdb.engine import DuckdbEngine
from core.infra.db.engines.duckdb.process_pool_scope import (
    duckdb_worker_pool_main_process,
    is_duckdb_backend,
    maybe_duckdb_worker_pool_scope,
    prepare_main_for_worker_pool,
    release_all_main_db_handles,
    release_worker_db_handles,
)
from core.infra.db.engines.duckdb.table_operator import DuckdbTableOperator

__all__ = [
    "DuckdbEngine",
    "DuckdbTableOperator",
    "DuckdbDomainCatalog",
    "DuckdbTableFileMap",
    "duckdb_worker_pool_main_process",
    "is_duckdb_backend",
    "maybe_duckdb_worker_pool_scope",
    "prepare_main_for_worker_pool",
    "release_all_main_db_handles",
    "release_worker_db_handles",
]
