"""
策略 JobPipeline 子进程：初始化只读 DataManager。

``invoke_execute`` 会在每个 job 前 ``DatabaseManager.reset_default()``（并 close 连接），
若 ``DataManager`` 单例仍标记为已初始化，会继续使用已关闭的 db → 读表报「数据库未初始化」。
"""
from __future__ import annotations

import logging
import multiprocessing as mp
import os
from copy import deepcopy
from typing import Any, Dict, Tuple

logger = logging.getLogger(__name__)

_PID_DATA_MANAGER: Dict[int, Any] = {}


def _database_config_for_worker() -> Dict[str, Any]:
    from core.infra.project_context import ConfigManager

    cfg = deepcopy(ConfigManager.load_database_config())
    if str(cfg.get("database_type") or "").lower() != "duckdb":
        return cfg
    duck = cfg.setdefault("duckdb", {})
    domains = duck.setdefault("domains", {})
    if isinstance(domains, dict):
        for block in domains.values():
            if isinstance(block, dict):
                block["read_only"] = True
    return cfg


def _connect_duckdb_data_domain_readonly(db: Any) -> None:
    from core.infra.db.engines._shared.config_parse import parse_database_config
    from core.infra.db.engines.duckdb.connector import DuckdbDomainConnection
    from core.infra.db.engines.duckdb.settings import DuckdbSettings

    parsed = parse_database_config(_database_config_for_worker())
    settings = DuckdbSettings.from_dict(parsed.get("duckdb") or parsed)
    eng = db.engine
    eng.connector._domains = {}
    shared = settings.shared_connector_dict()
    dom = settings.domains["data"]
    merged = dom.as_dict(shared)
    conn = DuckdbDomainConnection(merged, is_verbose=False, domain="data")
    conn.connect()
    eng.connector._domains["data"] = conn
    eng._initialized = True


def create_strategy_worker_data_manager() -> Any:
    """子进程专用 DataManager：只读 data 域（DuckDB）或完整 initialize（MySQL 等）。"""
    from core.infra.db import DatabaseManager
    from core.infra.db.engines.duckdb.engine import DuckdbEngine
    from core.infra.db.engines.factory import create_engine
    from core.modules.data_manager import DataManager
    from core.modules.data_manager.data_services import DataService

    db = DatabaseManager(config=_database_config_for_worker(), is_verbose=False)
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


def _close_worker_data_manager(data_mgr: Any) -> None:
    from core.infra.db import DatabaseManager
    from core.modules.data_manager import DataManager

    db = getattr(data_mgr, "db", None)
    if db is not None:
        try:
            db.close()
        except Exception as exc:
            logger.debug("strategy worker db.close: %s", exc)
    data_mgr.db = None
    data_mgr._initialized = False
    DatabaseManager.reset_default()
    if DataManager.get_instance() is data_mgr:
        DataManager.reset_instance()


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
        _close_worker_data_manager(cached)
        _PID_DATA_MANAGER.pop(pid, None)

    dm = create_strategy_worker_data_manager()
    _PID_DATA_MANAGER[pid] = dm
    return dm


def release_strategy_worker_runtime() -> None:
    """可选：子进程 job 结束时释放连接（与 Tag ``release_worker_runtime`` 同思路）。"""
    if mp.current_process().name == "MainProcess":
        return
    pid = os.getpid()
    cached = _PID_DATA_MANAGER.pop(pid, None)
    if cached is not None:
        _close_worker_data_manager(cached)
