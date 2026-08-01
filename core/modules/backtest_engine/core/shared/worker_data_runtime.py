"""Backtest worker 子进程 DataManager bootstrap（entity_based / slice_based 共用）。"""
from __future__ import annotations

import logging
import multiprocessing as mp
import os
import time
from typing import Any, Dict, Optional

from core.infra.db import Db
from core.infra.db.contracts import DatabaseManager

logger = logging.getLogger(__name__)

_PID_DATA_MANAGER: Dict[int, Any] = {}
_ATEXIT_REGISTERED = False


def _ensure_worker_atexit_registered() -> None:
    global _ATEXIT_REGISTERED
    if _ATEXIT_REGISTERED or mp.current_process().name == "MainProcess":
        return
    import atexit

    atexit.register(release_worker_runtime)
    _ATEXIT_REGISTERED = True


def _connect_duckdb_data_domain_readonly(db: Any) -> None:
    last_exc: Optional[BaseException] = None
    for attempt in range(1, 9):
        try:
            Db.duckdb.worker_pool.connect_domains(db, domains=("data",), read_only=True)
            return
        except Exception as exc:
            last_exc = exc
            msg = str(exc).lower()
            if "lock" not in msg and "conflicting" not in msg:
                raise
            if attempt < 8:
                time.sleep(0.25)
    if last_exc is not None:
        raise last_exc


def create_worker_data_manager() -> Any:
    """子进程专用 DataManager：DuckDB 只读 data 域，或 MySQL 等完整 initialize。"""
    from core.modules.data_manager import DataManager
    from core.modules.data_manager.data_services import DataService

    db = DatabaseManager(
        config=Db.duckdb.worker_pool.database_config_read_only(), is_verbose=False
    )
    db.engine = Db.engine.create(db.engine_meta)
    db.rebuild_storage_registry()
    if str(getattr(db.engine_meta, "engine_key", "") or "").lower() == "duckdb":
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


def bootstrap_worker_data_manager() -> Any:
    """子进程 job 入口：在 reset_default 之后重建 DataManager。"""
    if mp.current_process().name == "MainProcess":
        from core.modules.data_manager import DataManager

        return DataManager(is_verbose=False)

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
        release_worker_runtime()

    dm = create_worker_data_manager()
    _PID_DATA_MANAGER[pid] = dm
    _ensure_worker_atexit_registered()
    return dm


def release_worker_runtime() -> None:
    """子进程 worker 退出时释放 DB；job 之间复用连接，避免每 batch 重建。"""
    if mp.current_process().name == "MainProcess":
        return
    pid = os.getpid()
    cached = _PID_DATA_MANAGER.pop(pid, None)
    if cached is not None:
        Db.duckdb.worker_pool.release_worker_db_handles(cached)
        from core.modules.data_manager import DataManager

        if DataManager.get_instance() is cached:
            DataManager.reset_instance()


__all__ = [
    "bootstrap_worker_data_manager",
    "create_worker_data_manager",
    "release_worker_runtime",
]
