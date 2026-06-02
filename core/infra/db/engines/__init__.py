"""
Database Engines — per-backend 挂载架构。

对外入口：DatabaseManager.engine → DbEngineAbc.table_operator(name) → DbTableAbc
"""
from core.infra.db.engines.abc import DbEngineAbc, DbTableAbc
from core.infra.db.engines.factory import create_engine
from core.infra.db.engines.meta import EngineConfigMeta, build_engine_meta

__all__ = [
    "DbEngineAbc",
    "DbTableAbc",
    "EngineConfigMeta",
    "build_engine_meta",
    "create_engine",
]
