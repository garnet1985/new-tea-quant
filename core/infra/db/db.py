"""Db 门面（Facade）— infra.db 对外统一入口类。

实现位于 ``core/``；跨模块契约类型见 ``contracts.py``。
过渡期：包根仍 re-export ``DatabaseManager`` / ``DbBaseModel`` 等，调用方迁移完成后将只保留本门面。
"""

from __future__ import annotations

from typing import Any, Optional

from core.infra.db.core.db_manager import DatabaseManager
from core.infra.db.core.migrate_manager import MigrationManager


class ManagerNamespace:
    """数据库管理器命名空间（对应 DatabaseManager）。"""

    DatabaseManager = DatabaseManager

    @staticmethod
    def get_default(*, auto_init: bool = True) -> DatabaseManager:
        return DatabaseManager.get_default(auto_init=auto_init)

    @staticmethod
    def set_default(manager: DatabaseManager) -> None:
        DatabaseManager.set_default(manager)

    @staticmethod
    def reset_default() -> None:
        DatabaseManager.reset_default()

    @staticmethod
    def create(
        config: Optional[dict[str, Any]] = None, *, is_verbose: bool = False
    ) -> DatabaseManager:
        return DatabaseManager(config=config, is_verbose=is_verbose)


class MigrationNamespace:
    """Schema 迁移命名空间。

    CLI：``python -m core.infra.db.core.migrate_manager``。
    """

    MigrationManager = MigrationManager

    @staticmethod
    def build_plan(**kwargs: Any):
        return MigrationManager.build_plan(**kwargs)

    @staticmethod
    def run(**kwargs: Any):
        return MigrationManager.run(**kwargs)


class DuckdbNamespace:
    """DuckDB 跨模块协作入口。

    过渡期调用方仍可 ``from core.infra.db.core.engines.duckdb.process_pool_scope import ...``；
    后续收口到本 namespace。
    """

    @staticmethod
    def process_pool_module():
        """返回 ``process_pool_scope`` 模块（含 prepare/restore/maybe_scope 等）。"""
        from core.infra.db.core.engines.duckdb import process_pool_scope as pps

        return pps


class Db:
    """New Tea Quant（NTQ）数据库门面类（Facade：对外统一入口）。"""

    manager = ManagerNamespace
    migration = MigrationNamespace
    duckdb = DuckdbNamespace


__all__ = ["Db"]
