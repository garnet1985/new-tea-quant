"""子进程内 Tag stage（BacktestEngine execute_fn 内调用）。"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, Tuple

from core.infra.db.engines.duckdb.process_pool_scope import (
    connect_duckdb_domains,
    database_config_read_only,
    reconnect_main_database,
    release_main_for_workers,
    release_worker_db_handles,
    resume_main_database_with_retry,
    suspend_main_database,
    wait_pool_children_done,
)
from core.modules.data_contract.cache import ContractCacheManager
from core.modules.tag.engines.shared.staging.job_stager import TagJobStager, TagStageJob

logger = logging.getLogger(__name__)

_PID_STAGER: Dict[int, Tuple[Any, TagJobStager]] = {}


def _connect_worker_duckdb_domains(db: Any) -> None:
    """只连 data + tag（只读）；不连 strategy，避免与主进程 strategy.duckdb 写锁冲突。"""
    connect_duckdb_domains(db, domains=("data", "tag"), read_only=True)


def create_worker_data_manager() -> Any:
    """子进程只读 DuckDB（data+tag 域）+ 跳过 CREATE。"""
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
        _connect_worker_duckdb_domains(db)
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

    return dm


def release_worker_runtime() -> None:
    """子进程 job 结束：释放 Tag worker 连接（须在 execute finally 中调用）。"""
    import multiprocessing as mp

    if mp.current_process().name == "MainProcess":
        return
    pid = os.getpid()
    cached = _PID_STAGER.pop(pid, None)
    if cached is None:
        release_worker_db_handles()
        return
    data_mgr, _stager = cached
    release_worker_db_handles(data_mgr)


def get_worker_stager() -> TagJobStager:
    """当前子进程内复用 TagJobStager（每进程一条只读连接，非跨进程共享）。"""
    pid = os.getpid()
    cached = _PID_STAGER.get(pid)
    if cached is not None:
        return cached[1]
    data_mgr = create_worker_data_manager()
    stager = TagJobStager(data_mgr=data_mgr, contract_cache=ContractCacheManager())
    _PID_STAGER[pid] = (data_mgr, stager)
    return stager


def stage_payload_in_worker(payload: Dict[str, Any]) -> Dict[str, Any]:
    """在子进程执行 bulk/single stage，返回带 _inject 的 worker payload。"""
    job = TagStageJob(job_id=str(payload.get("_job_id") or "tag_worker"), payload=dict(payload))
    enriched = get_worker_stager().stage_job(job)
    return dict(enriched.payload)


def payload_needs_worker_stage(payload: Dict[str, Any]) -> bool:
    if not payload.get("_stage_in_worker"):
        return False
    if payload.get("_inject"):
        return False
    return True


def release_main_data_domain(data_mgr: Any) -> None:
    release_main_for_workers(data_mgr)


def reconnect_main_data_domain(data_mgr: Any) -> None:
    reconnect_main_database(data_mgr)


def digest_stage_in_worker_save_buffer(
    data_mgr: Any,
    save_buffer: Any,
    *,
    batch_size: int,
) -> float:
    """
    单次进程池结束后：仅 tag 域 resume → 落盘/缓冲写库 → suspend。

    运行期靠 spill 控内存，不在 worker 存活时打开主库。
    """
    has_pending = (
        save_buffer.pending_row_count > 0
        or getattr(save_buffer, "spill_count", 0) > 0
        or bool(getattr(save_buffer, "_spill_files", None))
    )
    if not has_pending:
        return 0.0
    wait_pool_children_done()
    resume_main_database_with_retry(data_mgr, tag_write_only=True)
    try:
        return float(
            save_buffer.persist_accumulated(
                data_mgr.stock.tags.save_batch,
                batch_size=batch_size,
            )
        )
    finally:
        suspend_main_database(data_mgr)
