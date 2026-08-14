"""
PgsqlTableOperator — PostgreSQL 表级 CRUD。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from core.infra.db.core.engines.shared.server_table_operator import (
    ServerTableOperatorBase,
)

if TYPE_CHECKING:
    from core.infra.db.core.engines.pgsql.engine import PgsqlEngine


class PgsqlTableOperator(ServerTableOperatorBase):
    database_type = "postgresql"
    supports_delete_limit = False

    def __init__(self, engine: "PgsqlEngine", table_name: str) -> None:
        super().__init__(engine, table_name)


__all__ = ["PgsqlTableOperator"]
