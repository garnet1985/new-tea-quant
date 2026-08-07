"""
PgsqlEngine — PostgreSQL 引擎编排（连接、DDL、写队列、table_operator）。
"""
from __future__ import annotations

from core.infra.db.core.engines.abc.table_abc import DbTableAbc
from core.infra.db.core.engines.meta import EngineConfigMeta
from core.infra.db.core.engines.pgsql.connector import PgsqlConnector
from core.infra.db.core.engines.pgsql.table_operator import PgsqlTableOperator
from core.infra.db.core.engines.shared.server_engine import ServerEngineBase


class PgsqlEngine(ServerEngineBase):
    engine_key = "postgresql"

    def _create_connector(self, meta: EngineConfigMeta, *, is_verbose: bool):
        return PgsqlConnector(meta.require_pgsql(), is_verbose=is_verbose)

    def _create_table_operator(self, table_name: str) -> DbTableAbc:
        return PgsqlTableOperator(self, table_name)
