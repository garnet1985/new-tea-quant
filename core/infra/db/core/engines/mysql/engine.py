"""
MysqlEngine — MySQL 引擎编排（连接、DDL、写队列、table_operator）。
"""
from __future__ import annotations

from core.infra.db.core.engines.abc.table_abc import DbTableAbc
from core.infra.db.core.engines.meta import EngineConfigMeta
from core.infra.db.core.engines.mysql.connector import MysqlConnector
from core.infra.db.core.engines.mysql.table_operator import MysqlTableOperator
from core.infra.db.core.engines.shared.server_engine import ServerEngineBase


class MysqlEngine(ServerEngineBase):
    engine_key = "mysql"

    def _create_connector(self, meta: EngineConfigMeta, *, is_verbose: bool):
        return MysqlConnector(meta.require_mysql(), is_verbose=is_verbose)

    def _create_table_operator(self, table_name: str) -> DbTableAbc:
        return MysqlTableOperator(self, table_name)
