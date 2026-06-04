"""
DuckDB 多进程（ProcessPool）主/子进程文件锁协作。

进程池运行前主进程须释放 ``.duckdb`` 连接，子进程以 ``read_only`` 打开；
池结束后主进程再 resume（可重试）。与 Tag/Strategy 业务无关，供 JobPipeline 等复用。

用法::

    from core.infra.db.engines.duckdb.process_pool_scope import (
        duckdb_worker_pool_main_process,
    )

    with duckdb_worker_pool_main_process(data_mgr):
        pipeline.run(jobs)

JobPipeline ``JobPipelineSettings.duckdb_process_pool_scope="auto"`` 时，
PROCESS 后端 + 配置为 duckdb 会自动套用上述 context。
"""
from __future__ import annotations

import logging
import multiprocessing as mp
import os
import time
from contextlib import contextmanager
from copy import deepcopy
from typing import Any, Iterator, Literal, Optional, Tuple

logger = logging.getLogger(__name__)

DuckdbProcessPoolScopeMode = Literal["auto", "on", "off"]

_MAIN_SUSPEND_DEPTH = 0


def is_duckdb_backend(data_mgr: Any = None) -> bool:
    if data_mgr is not None:
        db = getattr(data_mgr, "db", None)
        if db is not None:
            return str(db.config.get("database_type") or "").lower() == "duckdb"
    from core.infra.project_context import ConfigManager

    cfg = ConfigManager.load_database_config()
    return str(cfg.get("database_type") or "").lower() == "duckdb"


def resolve_data_manager(data_mgr: Optional[Any] = None) -> Any:
    from core.modules.data_manager import DataManager

    if data_mgr is not None:
        return data_mgr
    inst = DataManager.get_instance()
    if inst is not None:
        return inst
    return DataManager(is_verbose=False)


def should_apply_process_pool_scope(
    *,
    mode: DuckdbProcessPoolScopeMode,
    use_process_pool: bool,
    data_mgr: Optional[Any] = None,
) -> bool:
    if mode == "off":
        return False
    if mode == "on":
        return use_process_pool
    return use_process_pool and is_duckdb_backend(data_mgr)


def database_config_read_only() -> dict[str, Any]:
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


def connect_duckdb_domains(
    db: Any,
    *,
    domains: Tuple[str, ...],
    read_only: bool,
) -> None:
    """按域连接 DuckDB（不连未列出的域）。"""
    from core.infra.db.engines._shared.config_parse import parse_database_config
    from core.infra.db.engines.duckdb.connector import DuckdbDomainConnection
    from core.infra.db.engines.duckdb.settings import DuckdbSettings
    from core.infra.project_context import ConfigManager

    raw = ConfigManager.load_database_config()
    if read_only:
        raw = database_config_read_only()
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


def _collect_db_managers_from_data_mgr(data_mgr: Any) -> list[Any]:
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
    try:
        holder.db = None
    except Exception:
        pass


def _invalidate_data_service_db_refs(data_mgr: Any) -> None:
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


def release_all_main_db_handles(data_mgr: Any) -> None:
    """
    关闭主进程全部 DuckDB 连接（data_mgr、get_default、DataService / Model 缓存）。
    worker 池开跑前必须调用，否则子进程 read_only 会遇 Conflicting lock。
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
    """仅连接 tag 域写库，不打开 data.duckdb（波次 digest）。"""
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
    connect_duckdb_domains(db, domains=("tag",), read_only=False)
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


def wait_pool_children_done(*, timeout_sec: float = 15.0) -> None:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        alive = [p for p in mp.active_children() if p.is_alive()]
        if not alive:
            return
        time.sleep(0.05)
    alive = [p.name for p in mp.active_children() if p.is_alive()]
    if alive:
        logger.warning("进程池子进程仍未退出（可能影响 DuckDB 锁）: %s", alive[:8])


def prepare_main_for_worker_pool(data_mgr: Any) -> None:
    """进程池开跑前：等待遗留子进程退出、关闭主库、禁止 get_default(auto_init) 抢锁。"""
    from core.infra.db import DatabaseManager

    wait_pool_children_done(timeout_sec=30.0)
    release_all_main_db_handles(data_mgr)
    DatabaseManager._auto_init_enabled = False
    logger.debug("DuckDB worker 阶段：主进程已释放 data/tag 连接，已禁用 DB auto_init")


def restore_after_worker_pool() -> None:
    """进程池结束后恢复 get_default(auto_init)（具体连接由 resume_* 再打开）。"""
    from core.infra.db import DatabaseManager

    DatabaseManager._auto_init_enabled = True


def release_main_for_workers(data_mgr: Any) -> None:
    """短路径（探针等）：仅关闭主进程 DuckDB，不等待子进程、不改 auto_init。"""
    release_all_main_db_handles(data_mgr)


def reconnect_main_database(data_mgr: Any) -> None:
    resume_main_database(data_mgr)


def release_worker_db_handles(data_mgr: Optional[Any] = None) -> None:
    """
    子进程 job 结束：关闭本进程 DuckDB，避免 pool shutdown 后仍占文件锁。

    业务方在 execute 的 finally 中调用；``data_mgr`` 为 None 时仅 reset DatabaseManager。
    """
    if mp.current_process().name == "MainProcess":
        return
    from core.infra.db import DatabaseManager

    if data_mgr is not None:
        db = getattr(data_mgr, "db", None)
        if db is not None:
            try:
                db.close()
            except Exception as exc:
                logger.debug("worker db.close: %s", exc)
        data_mgr.db = None
        data_mgr._initialized = False
    DatabaseManager.reset_default()


@contextmanager
def duckdb_worker_pool_main_process(
    data_mgr: Optional[Any] = None,
    *,
    resume_main_after: bool = True,
    wait_children_timeout_sec: float = 30.0,
) -> Iterator[Any]:
    """
    包裹一次 ProcessPool 调度：进入前释放主进程锁，退出后等待子进程并可选 resume。

    可重入（嵌套调用只 prepare/resume 一次）。
    """
    global _MAIN_SUSPEND_DEPTH

    dm = resolve_data_manager(data_mgr)
    if not is_duckdb_backend(dm):
        yield dm
        return

    if _MAIN_SUSPEND_DEPTH > 0:
        _MAIN_SUSPEND_DEPTH += 1
        try:
            yield dm
        finally:
            _MAIN_SUSPEND_DEPTH -= 1
        return

    prepare_main_for_worker_pool(dm)
    _MAIN_SUSPEND_DEPTH = 1
    try:
        yield dm
    finally:
        _MAIN_SUSPEND_DEPTH = 0
        wait_pool_children_done(timeout_sec=wait_children_timeout_sec)
        restore_after_worker_pool()
        if resume_main_after:
            resume_main_database_with_retry(dm)


@contextmanager
def maybe_duckdb_worker_pool_scope(
    *,
    mode: DuckdbProcessPoolScopeMode = "auto",
    use_process_pool: bool,
    data_mgr: Optional[Any] = None,
    resume_main_after: bool = True,
) -> Iterator[Any]:
    """按 mode 决定是否进入 ``duckdb_worker_pool_main_process``。"""
    if not should_apply_process_pool_scope(
        mode=mode,
        use_process_pool=use_process_pool,
        data_mgr=data_mgr,
    ):
        yield resolve_data_manager(data_mgr)
        return
    with duckdb_worker_pool_main_process(
        data_mgr,
        resume_main_after=resume_main_after,
    ) as dm:
        yield dm
