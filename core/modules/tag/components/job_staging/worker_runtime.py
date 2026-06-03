"""子进程内 Tag stage（JobDispatcher execute 内调用）。"""
from __future__ import annotations

import logging
import multiprocessing as mp
import os
import time
from copy import deepcopy
from typing import Any, Callable, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

from core.infra.job_dispatcher.types import Job
from core.modules.data_contract.cache import ContractCacheManager
from core.modules.tag.components.job_staging.tag_job_stager import TagJobStager

# 每个子进程复用一套 DataManager + TagJobStager（不共享连接，仅少初始化）
_PID_STAGER: Dict[int, Tuple[Any, TagJobStager]] = {}


def _database_config_read_only() -> Dict[str, Any]:
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


def _connect_duckdb_domains(
    db: Any,
    *,
    domains: Tuple[str, ...],
    read_only: bool,
) -> None:
    """按域连接 DuckDB（不连未列出的域）。"""
    from core.infra.db.engines.duckdb.connector import DuckdbDomainConnection
    from core.infra.db.engines.duckdb.settings import DuckdbSettings
    from core.infra.db.engines._shared.config_parse import parse_database_config
    from core.infra.project_context import ConfigManager

    raw = ConfigManager.load_database_config()
    if read_only:
        raw = _database_config_read_only()
    parsed = parse_database_config(raw)
    settings = DuckdbSettings.from_dict(parsed.get("duckdb") or parsed)
    eng = db.engine
    eng.connector._domains = {}
    shared = settings.shared_connector_dict()
    for domain in domains:
        dom = settings.domains[domain]
        merged = dom.as_dict(shared)
        if not read_only:
            merged = dict(merged)
            merged.pop("read_only", None)
            merged["read_only"] = False
        conn = DuckdbDomainConnection(merged, is_verbose=False, domain=domain)
        conn.connect()
        eng.connector._domains[domain] = conn
    eng._initialized = True


def _connect_worker_duckdb_domains(db: Any) -> None:
    """只连 data + tag（只读）；不连 strategy，避免与主进程 strategy.duckdb 写锁冲突。"""
    _connect_duckdb_domains(db, domains=("data", "tag"), read_only=True)


def create_worker_data_manager() -> Any:
    """子进程只读 DuckDB（data+tag 域）+ 跳过 CREATE。"""
    from core.infra.db import DatabaseManager
    from core.infra.db.engines.duckdb.engine import DuckdbEngine
    from core.infra.db.engines.factory import create_engine
    from core.modules.data_manager import DataManager
    from core.modules.data_manager.data_services import DataService

    db = DatabaseManager(config=_database_config_read_only(), is_verbose=False)
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


def _collect_db_managers_from_data_mgr(data_mgr: Any) -> list[Any]:
    """收集主进程上可能仍占 DuckDB 文件锁的 DatabaseManager（含缓存 Model.db）。"""
    from core.infra.db import DatabaseManager

    found: list[Any] = []
    seen: set[int] = set()

    def add(db: Any) -> None:
        if db is None or not isinstance(db, DatabaseManager):
            return
        key = id(db)
        if key in seen:
            return
        seen.add(key)
        found.append(db)

    add(getattr(data_mgr, "db", None))
    add(DatabaseManager._default_instance)

    ds = getattr(data_mgr, "_data_service", None)
    service_blocks: list[Any] = []
    if ds is not None:
        for name in ("stock", "macro", "calendar", "index", "db_cache", "backup_restore"):
            service_blocks.append(getattr(ds, name, None))
    for block in service_blocks:
        if block is None:
            continue
        add(getattr(block, "db", None))
        for attr in dir(block):
            try:
                child = getattr(block, attr)
            except Exception:
                continue
            if isinstance(child, DatabaseManager):
                add(child)
            else:
                add(getattr(child, "db", None))
    return found


def _clear_db_attr_holder(holder: Any) -> None:
    """仅断开引用（关闭由 release_all_main_db_handles 统一完成）。"""
    try:
        holder.db = None
    except Exception:
        pass


def release_all_main_db_handles(data_mgr: Any) -> None:
    """
    关闭主进程全部 DuckDB 连接（data_mgr、get_default、DataService / Model 缓存）。
    worker 池开跑前必须调用，否则子进程 read_only stage 会遇 Conflicting lock。
    """
    from core.infra.db import DatabaseManager

    for db in _collect_db_managers_from_data_mgr(data_mgr):
        try:
            db.close()
        except Exception as exc:
            logger.debug("release_all db.close: %s", exc)
    data_mgr.db = None
    data_mgr._initialized = False
    _invalidate_data_service_db_refs(data_mgr)
    DatabaseManager.reset_default()


def suspend_main_database(data_mgr: Any) -> None:
    """
    关闭主进程 DatabaseManager，让子进程独占 DuckDB 文件（read_only）。
    on_result 前须 resume_main_database 再写 tag。
    """
    release_all_main_db_handles(data_mgr)


def _attach_data_manager_db(data_mgr: Any, db: Any) -> None:
    from core.infra.db import DatabaseManager
    from core.modules.data_manager.data_services import DataService

    data_mgr.db = db
    data_mgr._data_service = DataService(data_mgr)
    data_mgr._initialized = True
    DatabaseManager.set_default(db)


def resume_main_database(data_mgr: Any) -> None:
    """恢复主进程全库可写连接。"""
    db = getattr(data_mgr, "db", None)
    if db is not None and getattr(db, "_initialized", False):
        return
    from core.infra.db import DatabaseManager

    db = DatabaseManager(is_verbose=bool(getattr(data_mgr, "is_verbose", False)))
    db.initialize()
    _attach_data_manager_db(data_mgr, db)


def resume_main_database_tag_write_only(data_mgr: Any) -> None:
    """
    波次 digest：仅连接 tag 域写 sys_tag_value，不打开 data.duckdb。

    避免主进程占 data 锁导致下一波 worker 无法 read_only stage。
    """
    from core.infra.db import DatabaseManager
    from core.infra.db.engines.duckdb.engine import DuckdbEngine
    from core.infra.db.engines.factory import create_engine

    db = getattr(data_mgr, "db", None)
    if (
        db is not None
        and getattr(db, "_initialized", False)
        and getattr(db.engine, "connector", None) is not None
        and "tag" in getattr(db.engine.connector, "_domains", {})
        and "data" not in getattr(db.engine.connector, "_domains", {})
    ):
        return

    if db is not None:
        db.close()

    db = DatabaseManager(is_verbose=bool(getattr(data_mgr, "is_verbose", False)))
    db.engine = create_engine(db.engine_meta)
    db.rebuild_storage_registry()
    if isinstance(db.engine, DuckdbEngine):
        db.engine.rebuild_table_file_map(
            table_to_domain=db.storage_registry.table_to_domain
        )
    _connect_duckdb_domains(db, domains=("tag",), read_only=False)
    db._initialized = True
    _attach_data_manager_db(data_mgr, db)


def resume_main_database_with_retry(
    data_mgr: Any,
    *,
    attempts: int = 8,
    delay_sec: float = 0.25,
    tag_write_only: bool = False,
) -> None:
    """worker 退出后偶发仍占 DuckDB 锁，短暂重试 resume。"""
    resume_fn = (
        resume_main_database_tag_write_only
        if tag_write_only
        else resume_main_database
    )
    last_exc: Optional[BaseException] = None
    for attempt in range(1, attempts + 1):
        try:
            resume_fn(data_mgr)
            return
        except Exception as exc:
            last_exc = exc
            msg = str(exc).lower()
            if "lock" not in msg and "conflicting" not in msg:
                raise
            if attempt < attempts:
                logger.info(
                    "主库 resume 遇锁 (attempt %s/%s)，等待 worker 释放…",
                    attempt,
                    attempts,
                )
                time.sleep(delay_sec)
    if last_exc is not None:
        raise last_exc


def _invalidate_data_service_db_refs(data_mgr: Any) -> None:
    """主进程 suspend 后清掉 DataService / 子服务 / Model 上缓存的 db 引用。"""
    ds = getattr(data_mgr, "_data_service", None)
    blocks: list[Any] = []
    if ds is not None:
        for name in ("stock", "macro", "calendar", "index", "db_cache", "backup_restore"):
            blocks.append(getattr(ds, name, None))
    for block in blocks:
        if block is None:
            continue
        _clear_db_attr_holder(block)
        for attr in dir(block):
            try:
                child = getattr(block, attr)
            except Exception:
                continue
            if child is not None and hasattr(child, "db"):
                _clear_db_attr_holder(child)


def prepare_main_for_duckdb_workers(data_mgr: Any) -> None:
    """
    进程池开跑前：等待遗留子进程退出、关闭主库、禁止 get_default(auto_init) 抢锁。
    """
    from core.infra.db import DatabaseManager

    _wait_pool_children_done(timeout_sec=30.0)
    release_all_main_db_handles(data_mgr)
    DatabaseManager._auto_init_enabled = False
    logger.info("DuckDB worker 阶段：主进程已释放 data/tag 连接，已禁用 DB auto_init")


def restore_main_after_duckdb_worker_pool() -> None:
    """进程池结束后恢复 get_default(auto_init)（具体连接由 resume_* 再打开）。"""
    from core.infra.db import DatabaseManager

    DatabaseManager._auto_init_enabled = True


def release_main_duckdb_domains_for_workers(data_mgr: Any) -> None:
    """关闭主进程 DuckDB（探针等短路径；全量 worker 池请用 prepare_main_for_duckdb_workers）。"""
    release_all_main_db_handles(data_mgr)


def reconnect_main_duckdb_domains(data_mgr: Any) -> None:
    resume_main_database(data_mgr)


def release_worker_runtime() -> None:
    """
    子进程 job 结束：关闭本进程 DuckDB，避免 pool shutdown 后仍占 data.duckdb 锁。

    须在 _execute_single_job 的 finally 中调用（stage_in_worker）。
    """
    if mp.current_process().name == "MainProcess":
        return
    from core.infra.db import DatabaseManager

    pid = os.getpid()
    cached = _PID_STAGER.pop(pid, None)
    if cached is None:
        DatabaseManager.reset_default()
        return
    data_mgr, _stager = cached
    db = getattr(data_mgr, "db", None)
    if db is not None:
        try:
            db.close()
        except Exception as exc:
            logger.debug("worker db.close: %s", exc)
    data_mgr.db = None
    data_mgr._initialized = False
    DatabaseManager.reset_default()


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
    job = Job(job_id=str(payload.get("_job_id") or "tag_worker"), payload=dict(payload))
    enriched = get_worker_stager().stage_job(job)
    return dict(enriched.payload)


def payload_needs_worker_stage(payload: Dict[str, Any]) -> bool:
    if not payload.get("_stage_in_worker"):
        return False
    if payload.get("_inject"):
        return False
    return True


def release_main_data_domain(data_mgr: Any) -> None:
    """兼容别名：释放 data+tag 域。"""
    release_main_duckdb_domains_for_workers(data_mgr)


def reconnect_main_data_domain(data_mgr: Any) -> None:
    """兼容别名：恢复缺失域。"""
    reconnect_main_duckdb_domains(data_mgr)


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
    _wait_pool_children_done()
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


def _wait_pool_children_done(*, timeout_sec: float = 15.0) -> None:
    """进程池 shutdown 后等待子进程退出（一次性收尾，非波次轮询）。"""
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        alive = [p for p in mp.active_children() if p.is_alive()]
        if not alive:
            return
        time.sleep(0.05)
    alive = [p.name for p in mp.active_children() if p.is_alive()]
    if alive:
        logger.warning("进程池子进程仍未退出（可能影响 DuckDB 锁）: %s", alive[:8])
