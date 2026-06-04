"""
策略 JobPipeline 子进程：初始化只读 DataManager。

主进程 DuckDB 文件锁由 ``JobPipelineSettings.duckdb_process_pool_scope``（默认 auto）
或 ``core.infra.db.engines.duckdb.process_pool_scope`` 处理。
"""
from __future__ import annotations

import logging
import multiprocessing as mp
import os
from typing import Any, Dict, Optional, Tuple

from core.infra.db.engines.duckdb.process_pool_scope import (
    connect_duckdb_domains,
    database_config_read_only,
    release_worker_db_handles,
)

logger = logging.getLogger(__name__)

_PID_DATA_MANAGER: Dict[int, Any] = {}


def _connect_duckdb_data_domain_readonly(db: Any) -> None:
    connect_duckdb_domains(db, domains=("data",), read_only=True)


def create_strategy_worker_data_manager() -> Any:
    """子进程专用 DataManager：只读 data 域（DuckDB）或完整 initialize（MySQL 等）。"""
    from core.infra.db import DatabaseManager
    from core.infra.db.engines.duckdb.engine import DuckdbEngine
    from core.infra.db.engines.factory import create_engine
    from core.modules.data_manager import DataManager
    from core.modules.data_manager.data_services import DataService

    db = DatabaseManager(config=database_config_read_only(), is_verbose=False)
    db.engine = create_engine(db.engine_meta)
    db.rebuild_storage_registry()
    if isinstance(db.engine, DuckdbEngine):
        db.engine.rebuild_table_file_map(
            table_to_domain=db.storage_registry.table_to_domain
        )
        _connect_duckdb_data_domain_readonly(db)
        db._initialized = True
    else:
        db.initialize()
    DatabaseManager.set_default(db)

    dm = DataManager.__new__(DataManager)
    dm.is_verbose = False
    dm.db = db
    dm._initialized = False
    dm._table_cache = {}
    dm._data_service = None
    if hasattr(db.engine, "_initialized"):
        db.engine._initialized = False
    dm._discover_tables()
    dm._data_service = DataService(dm)
    dm._initialized = True
    if hasattr(db.engine, "_initialized"):
        db.engine._initialized = True

    DataManager._instance = dm
    return dm


def bootstrap_strategy_worker_data_manager() -> Any:
    """
    在子进程 execute 入口调用：在 ``reset_default`` 之后重建 DataManager。

    按进程缓存；若默认 db 已被 reset 则重建。
    """
    if mp.current_process().name == "MainProcess":
        from core.modules.data_manager import DataManager

        return DataManager(is_verbose=False)

    from core.infra.db import DatabaseManager

    pid = os.getpid()
    default = DatabaseManager._default_instance
    cached = _PID_DATA_MANAGER.get(pid)
    if (
        cached is not None
        and default is not None
        and getattr(cached, "db", None) is default
        and default._initialized
    ):
        return cached

    if cached is not None:
        release_strategy_worker_runtime()

    dm = create_strategy_worker_data_manager()
    _PID_DATA_MANAGER[pid] = dm
    return dm


def release_strategy_worker_runtime() -> None:
    """子进程 job 结束时释放连接。"""
    if mp.current_process().name == "MainProcess":
        return
    pid = os.getpid()
    cached = _PID_DATA_MANAGER.pop(pid, None)
    if cached is not None:
        release_worker_db_handles(cached)
        from core.modules.data_manager import DataManager

        if DataManager.get_instance() is cached:
            DataManager.reset_instance()
