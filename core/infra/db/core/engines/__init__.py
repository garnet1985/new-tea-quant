"""
Database Engines — per-backend 挂载架构。

对外入口：DatabaseManager.engine → DbEngineAbc.table_operator(name) → DbTableAbc
公开构造：``EngineConfigMeta.from_raw_config`` / ``EngineFactory.create``（或门面 ``Db.engine``）。
"""
from core.infra.db.core.engines.abc import DbEngineAbc, DbTableAbc
from core.infra.db.core.engines.factory import EngineFactory
from core.infra.db.core.engines.meta import EngineConfigMeta

__all__ = [
    "DbEngineAbc",
    "DbTableAbc",
    "EngineConfigMeta",
    "EngineFactory",
]
