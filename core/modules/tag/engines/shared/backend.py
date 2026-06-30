"""Tag 运行时 backend 探测。"""
from __future__ import annotations

from typing import Any, Optional

from core.modules.data_manager import DataManager


def configured_database_type(data_mgr: Optional[DataManager] = None) -> str:
    db = getattr(data_mgr, "db", None) if data_mgr else None
    if db is not None:
        return str(db.config.get("database_type") or "").lower()
    from core.infra.project_context import ProjectContext

    return str(ProjectContext.config.load_database_config().get("database_type") or "").lower()


def backend_is_duckdb(data_mgr: DataManager) -> bool:
    return configured_database_type(data_mgr) == "duckdb"
