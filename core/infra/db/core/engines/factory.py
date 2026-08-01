"""
Engine 工厂：按 EngineConfigMeta.engine_key 挂载具体 Engine。
"""
from __future__ import annotations

from core.infra.db.core.engines.abc.engine_abc import DbEngineAbc
from core.infra.db.core.engines.meta import EngineConfigMeta


def create_engine(meta: EngineConfigMeta) -> DbEngineAbc:
    """根据 meta.engine_key 构造 Engine 实例（未 initialize）。"""
    key = str(meta.engine_key).lower()
    is_verbose = bool(meta.options.get("is_verbose", False))

    if key == "mysql":
        from core.infra.db.core.engines.mysql.engine import MysqlEngine

        return MysqlEngine(meta, is_verbose=is_verbose)

    if key == "postgresql":
        from core.infra.db.core.engines.pgsql.engine import PgsqlEngine

        return PgsqlEngine(meta, is_verbose=is_verbose)

    if key == "duckdb":
        from core.infra.db.core.engines.duckdb.engine import DuckdbEngine

        return DuckdbEngine(meta, is_verbose=is_verbose)

    raise ValueError(
        f"不支持的 engine_key: {key!r}，"
        f"支持: mysql, postgresql, duckdb"
    )
