"""
MysqlTableOperator — MySQL 表级 CRUD。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from core.infra.db.core.engines.shared.server_table_operator import (
    ServerTableOperatorBase,
)

if TYPE_CHECKING:
    from core.infra.db.core.engines.mysql.engine import MysqlEngine


class MysqlTableOperator(ServerTableOperatorBase):
    database_type = "mysql"
    supports_delete_limit = True

    def __init__(self, engine: "MysqlEngine", table_name: str) -> None:
        super().__init__(engine, table_name)


__all__ = ["MysqlTableOperator"]
