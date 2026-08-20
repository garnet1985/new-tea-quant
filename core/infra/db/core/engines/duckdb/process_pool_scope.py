"""
DuckDB 多进程（ProcessPool）主/子进程文件锁协作。

进程池运行前主进程须释放 ``.duckdb`` 连接，子进程以 ``read_only`` 打开；
池结束后主进程再 resume（可重试）。与 Tag/Strategy 业务无关，供 JobPipeline 等复用。

用法::

    from core.infra.db.core.engines.duckdb.process_pool_scope import DuckdbWorkerPool

    with DuckdbWorkerPool.duckdb_worker_pool_main_process(data_mgr):
        pipeline.run(jobs)

JobPipeline ``JobPipelineSettings.duckdb_process_pool_scope="auto"`` 时，
PROCESS 后端 + 配置为 duckdb 会自动套用上述 context。
"""
from __future__ import annotations

import logging
import multiprocessing as mp
import os
import threading
import time
from contextlib import contextmanager
from copy import deepcopy
from typing import Any, Callable, Iterator, Literal, Optional, Tuple

logger = logging.getLogger(__name__)

DuckdbProcessPoolScopeMode = Literal["auto", "on", "off"]

# 由上层（通常 DataManager）注册：resolve(*, allow_create: bool) -> holder | None
_HolderResolver = Callable[..., Any]


class DuckdbWorkerPool:
    """DuckDB ProcessPool 主/子进程文件锁协作（实现类；公开入口 Db.duckdb.worker_pool）。"""

    CONFIG_OVERLAY_ENV = "NTQ_DATABASE_CONFIG_JSON"
    _main_suspend_depth = 0
    _suspend_thread_ident: Optional[int] = None
    _holder_resolver: Optional[_HolderResolver] = None

    @staticmethod
    def set_holder_resolver(resolver: Optional[_HolderResolver]) -> None:
        """注册应用层 holder 解析（如 DataManager 单例）。infra 不 import modules。"""
        DuckdbWorkerPool._holder_resolver = resolver

    @staticmethod
    def resolve_holder(
        data_mgr: Optional[Any] = None,
        *,
        allow_create: bool = False,
    ) -> Any:
        """解析 pool 协作对象（须有 ``.db`` 等 duck-type 面）。"""
        if data_mgr is not None:
            return data_mgr
        fn = DuckdbWorkerPool._holder_resolver
        if fn is None:
            return None
        return fn(allow_create=allow_create)

    @staticmethod
    def is_main_duckdb_worker_pool_active() -> bool:
        """主进程是否处于 DuckDB ProcessPool suspend（子进程读库）阶段。"""
        return DuckdbWorkerPool._main_suspend_depth > 0


    @staticmethod
    def wait_for_main_duckdb_worker_pool_end(*, timeout_sec: float = 30.0) -> None:
        """其它线程在 suspend 期间不得打开 DuckDB 写连接；阻塞直到 worker 池结束。

        持有 suspend 的同一线程再 ``DataManager()`` 会自锁，直接失败（勿长时间 sleep）。
        等待可被 Ctrl+C 打断（``interrupt_requested`` / ``KeyboardInterrupt``）。
        """
        if DuckdbWorkerPool._main_suspend_depth <= 0:
            return
        owner = DuckdbWorkerPool._suspend_thread_ident
        if owner is not None and threading.get_ident() == owner:
            raise RuntimeError(
                "DuckDB 已为 ProcessPool 释放主连接：当前线程禁止再打开主库"
            )
        deadline = time.monotonic() + max(0.0, float(timeout_sec))
        while DuckdbWorkerPool._main_suspend_depth > 0:
            try:
                from core.ui.process_cleanup import interrupt_requested

                if interrupt_requested():
                    raise KeyboardInterrupt
            except ImportError:
                pass
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    "等待 DuckDB ProcessPool 主进程释放文件锁超时 "
                    f"({timeout_sec}s)"
                )
            # 短 sleep，便于 SIGINT / KeyboardInterrupt 在 Windows 上及时送达
            time.sleep(0.05)


    @staticmethod
    def is_duckdb_backend(data_mgr: Any = None) -> bool:
        """True when the live DB (or ProjectContext) is DuckDB.

        Prefer an attached holder / ``db`` over ProjectContext so overlays
        (e.g. BE ``__performance__`` temp DuckDB while userspace is MySQL) still
        enable ProcessPool file-lock scope.
        """
        dm = data_mgr if data_mgr is not None else DuckdbWorkerPool.resolve_holder(None)
        if dm is not None:
            db = getattr(dm, "db", None)
            if db is not None:
                return str(db.config.get("database_type") or "").lower() == "duckdb"
        from core.infra.project_context import ProjectContext

        cfg = ProjectContext.config.load_database_config()
        return str(cfg.get("database_type") or "").lower() == "duckdb"


    @staticmethod
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
        return use_process_pool and DuckdbWorkerPool.is_duckdb_backend(data_mgr)


    # Spawn workers inherit env; BE __performance__ (and similar) publish a full
    # database config overlay here so workers do not touch userspace business DB.

    @staticmethod
    def install_config_overlay(cfg: dict[str, Any]) -> None:
        """Publish ``cfg`` via env for spawn workers and ``database_config_read_only``."""
        import json
        import os

        os.environ[DuckdbWorkerPool.CONFIG_OVERLAY_ENV] = json.dumps(cfg, ensure_ascii=False)


    @staticmethod
    def database_config_read_only() -> dict[str, Any]:
        import json
        import os

        from core.infra.project_context import ProjectContext

        raw_overlay = str(os.environ.get(DuckdbWorkerPool.CONFIG_OVERLAY_ENV) or "").strip()
        if raw_overlay:
            cfg = deepcopy(json.loads(raw_overlay))
        else:
            cfg = deepcopy(ProjectContext.config.load_database_config())
        if str(cfg.get("database_type") or "").lower() != "duckdb":
            return cfg
        duck = cfg.setdefault("duckdb", {})
        domains = duck.setdefault("domains", {})
        if isinstance(domains, dict):
            for block in domains.values():
                if isinstance(block, dict):
                    block["read_only"] = True
        return cfg


    @staticmethod
    def connect_duckdb_domains(
        db: Any,
        *,
        domains: Tuple[str, ...],
        read_only: bool,
    ) -> None:
        """按域连接 DuckDB（不连未列出的域）。"""
        from core.infra.db.core.engines.shared.config_parse import parse_database_config
        from core.infra.db.core.engines.duckdb.connector import DuckdbDomainConnection
        from core.infra.db.core.engines.duckdb.settings import DuckdbSettings
        from core.infra.project_context import ProjectContext

        raw = ProjectContext.config.load_database_config()
        if read_only:
            raw = DuckdbWorkerPool.database_config_read_only()
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


    @staticmethod
    def _collect_db_managers_from_data_mgr(data_mgr: Any) -> list[Any]:
        from core.infra.db.core.db_manager import DatabaseManager

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


    @staticmethod
    def _clear_db_attr_holder(holder: Any) -> None:
        try:
            holder.db = None
        except Exception:
            pass


    @staticmethod
    def _invalidate_data_service_db_refs(data_mgr: Any) -> None:
        ds = getattr(data_mgr, "_data_service", None)
        blocks: list[Any] = []
        if ds is not None:
            for name in ("stock", "macro", "calendar", "index", "db_cache", "backup_restore"):
                blocks.append(getattr(ds, name, None))
        for block in blocks:
            if block is None:
                continue
            DuckdbWorkerPool._clear_db_attr_holder(block)
            for attr in dir(block):
                try:
                    child = getattr(block, attr)
                except Exception:
                    continue
                if child is not None and hasattr(child, "db"):
                    DuckdbWorkerPool._clear_db_attr_holder(child)


    @staticmethod
    def release_all_main_db_handles(data_mgr: Any) -> None:
        """
        关闭主进程全部 DuckDB 连接（data_mgr、get_default、DataService / Model 缓存）。
        worker 池开跑前必须调用，否则子进程 read_only 会遇 Conflicting lock。
        """
        from core.infra.db.core.db_manager import DatabaseManager

        found = DuckdbWorkerPool._collect_db_managers_from_data_mgr(data_mgr)
        closed_ids: set[int] = set()
        for db in found:
            try:
                db.close()
                closed_ids.add(id(db))
            except Exception as exc:
                logger.debug("release_all db.close: %s", exc)
        if data_mgr is not None:
            try:
                data_mgr.db = None
                data_mgr._initialized = False
                DuckdbWorkerPool._invalidate_data_service_db_refs(data_mgr)
            except Exception:
                pass

        default_db = DatabaseManager._default_instance
        if default_db is not None:
            if id(default_db) not in closed_ids:
                try:
                    default_db.close()
                except Exception as exc:
                    logger.debug("release_all default db.close: %s", exc)
            DatabaseManager.reset_default()


    @staticmethod
    def release_all_process_duckdb_handles(data_mgr: Any = None) -> None:
        """进程内 holder / DatabaseManager 句柄（BFF refresh / 并发工作台）。"""
        from core.infra.db.core.db_manager import DatabaseManager

        DuckdbWorkerPool.wait_pool_children_done(timeout_sec=30.0)
        holders: list[Any] = []
        if data_mgr is not None:
            holders.append(data_mgr)
        resolved = DuckdbWorkerPool.resolve_holder(None, allow_create=False)
        if resolved is not None and all(resolved is not h for h in holders):
            holders.append(resolved)
        for holder in holders:
            DuckdbWorkerPool.release_all_main_db_handles(holder)
        if DatabaseManager._default_instance is not None:
            try:
                DatabaseManager._default_instance.close()
            except Exception as exc:
                logger.debug("release_all_process default db.close: %s", exc)
            DatabaseManager.reset_default()


    @staticmethod
    def suspend_main_database(data_mgr: Any) -> None:
        DuckdbWorkerPool.release_all_main_db_handles(data_mgr)


    @staticmethod
    def _attach_holder_db(data_mgr: Any, db: Any) -> None:
        """把 ``db`` 挂回 holder（duck-type；可选 ``bind_as_default_instance``）。"""
        from core.infra.db.core.db_manager import DatabaseManager

        data_mgr.db = db
        if not getattr(data_mgr, "_table_cache", None):
            discover = getattr(data_mgr, "_discover_tables", None)
            if callable(discover):
                discover()
        attach = getattr(data_mgr, "attach_data_service", None)
        if callable(attach):
            attach()
        data_mgr._initialized = True
        DatabaseManager.set_default(db)
        bind = getattr(data_mgr, "bind_as_default_instance", None)
        if callable(bind):
            bind()

    @staticmethod
    def resume_main_database(data_mgr: Any) -> None:
        """恢复主进程全库可写连接。"""
        db = getattr(data_mgr, "db", None)
        if db is not None and getattr(db, "_initialized", False):
            return
        from core.infra.db.core.db_manager import DatabaseManager

        db = DatabaseManager(is_verbose=bool(getattr(data_mgr, "is_verbose", False)))
        db.initialize()
        DuckdbWorkerPool._attach_holder_db(data_mgr, db)


    @staticmethod
    def resume_main_database_tag_write_only(data_mgr: Any) -> None:
        """仅连接 tag 域写库，不打开 data.duckdb（波次 digest）。"""
        from core.infra.db.core.db_manager import DatabaseManager
        from core.infra.db.core.engines.duckdb.engine import DuckdbEngine
        from core.infra.db.core.engines.factory import EngineFactory

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
        db.engine = EngineFactory.create(db.engine_meta)
        db.rebuild_storage_registry()
        if isinstance(db.engine, DuckdbEngine):
            db.engine.rebuild_table_file_map(
                table_to_domain=db.storage_registry.table_to_domain
            )
        DuckdbWorkerPool.connect_duckdb_domains(db, domains=("tag",), read_only=False)
        db._initialized = True
        DuckdbWorkerPool._attach_holder_db(data_mgr, db)


    @staticmethod
    def resume_main_database_with_retry(
        data_mgr: Any = None,
        *,
        attempts: int = 8,
        delay_sec: float = 0.25,
        tag_write_only: bool = False,
    ) -> None:
        """worker 退出后偶发仍占 DuckDB 锁，短暂重试 resume。"""
        dm = DuckdbWorkerPool.resolve_holder(data_mgr, allow_create=True)
        if dm is None:
            raise RuntimeError(
                "resume_main_database_with_retry 需要 holder "
                "（传入 data_mgr 或注册 set_holder_resolver）"
            )
        resume_fn = (
            DuckdbWorkerPool.resume_main_database_tag_write_only
            if tag_write_only
            else DuckdbWorkerPool.resume_main_database
        )
        last_exc: Optional[BaseException] = None
        for attempt in range(1, attempts + 1):
            try:
                resume_fn(dm)
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


    @staticmethod
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
            try:
                from core.ui.process_cleanup import terminate_multiprocessing_children

                terminate_multiprocessing_children(grace_sec=2.0)
            except Exception as exc:
                logger.debug("terminate_multiprocessing_children: %s", exc)


    @staticmethod
    def ensure_holder_restored(data_mgr: Any = None) -> Any:
        """
        ProcessPool 或 Ctrl+C 后恢复主进程 DatabaseManager + holder 表缓存。

        若 ``data_mgr`` 已有可写连接则仅补全 ``_table_cache`` / DataService（duck-type）。
        应用层首选 ``DataManager.ensure_restored_after_worker_pool``。
        """
        if not DuckdbWorkerPool.is_duckdb_backend(data_mgr):
            return DuckdbWorkerPool.resolve_holder(data_mgr, allow_create=True)

        dm = DuckdbWorkerPool.resolve_holder(data_mgr, allow_create=True)
        if dm is None:
            return None

        db = getattr(dm, "db", None)
        if db is not None and getattr(db, "_initialized", False):
            if not getattr(dm, "_table_cache", None):
                discover = getattr(dm, "_discover_tables", None)
                if callable(discover):
                    discover()
            if getattr(dm, "_data_service", None) is None:
                attach = getattr(dm, "attach_data_service", None)
                if callable(attach):
                    attach()
            dm._initialized = True
            bind = getattr(dm, "bind_as_default_instance", None)
            if callable(bind):
                bind()
            return dm

        DuckdbWorkerPool.resume_main_database_with_retry(dm)
        return dm

    # 兼容旧名
    ensure_data_manager_restored = ensure_holder_restored


    @staticmethod
    def recover_after_worker_pool_interrupt(data_mgr: Any = None) -> None:
        """CLI / 工作台 Ctrl+C：终止遗留 worker、恢复 auto_init 与主库连接。"""
        
        DuckdbWorkerPool._main_suspend_depth = 0
        DuckdbWorkerPool._suspend_thread_ident = None
        try:
            from core.ui.process_cleanup import terminate_multiprocessing_children

            terminate_multiprocessing_children(grace_sec=2.0)
        except Exception as exc:
            logger.debug("terminate_multiprocessing_children: %s", exc)
        DuckdbWorkerPool.wait_pool_children_done(timeout_sec=30.0)
        DuckdbWorkerPool.restore_after_worker_pool()
        if not DuckdbWorkerPool.is_duckdb_backend(data_mgr):
            return
        try:
            dm = DuckdbWorkerPool.ensure_data_manager_restored(data_mgr)
            db = getattr(dm, "db", None)
            if db is not None and hasattr(db, "checkpoint_duckdb"):
                db.checkpoint_duckdb()
        except Exception as exc:
            logger.warning("DuckDB 中断恢复未完成: %s", exc)


    @staticmethod
    def _finalize_worker_pool_main_process(
        data_mgr: Any,
        *,
        resume_main_after: bool,
        wait_children_timeout_sec: float,
    ) -> None:
        
        DuckdbWorkerPool._main_suspend_depth = 0
        DuckdbWorkerPool._suspend_thread_ident = None
        try:
            DuckdbWorkerPool.wait_pool_children_done(timeout_sec=wait_children_timeout_sec)
        finally:
            DuckdbWorkerPool.restore_after_worker_pool()
        if not resume_main_after:
            return
        try:
            dm = DuckdbWorkerPool.ensure_data_manager_restored(data_mgr)
            db = getattr(dm, "db", None)
            if db is not None and hasattr(db, "checkpoint_duckdb"):
                db.checkpoint_duckdb()
        except Exception as exc:
            logger.warning("DuckDB ProcessPool 收尾恢复失败: %s", exc)


    @staticmethod
    def prepare_main_for_worker_pool(data_mgr: Any = None) -> None:
        """进程池开跑前：等待遗留子进程退出、关闭主库、禁止 get_default(auto_init) 抢锁。"""
        from core.infra.db.core.db_manager import DatabaseManager

        DuckdbWorkerPool.release_all_process_duckdb_handles(data_mgr)
        DatabaseManager._auto_init_enabled = False
        logger.debug("DuckDB worker 阶段：主进程已释放 data/tag 连接，已禁用 DB auto_init")


    @staticmethod
    def restore_after_worker_pool() -> None:
        """进程池结束后恢复 get_default(auto_init)（具体连接由 resume_* 再打开）。"""
        from core.infra.db.core.db_manager import DatabaseManager

        DatabaseManager._auto_init_enabled = True


    @staticmethod
    def release_main_for_workers(data_mgr: Any) -> None:
        """短路径（探针等）：仅关闭主进程 DuckDB，不等待子进程、不改 auto_init。"""
        DuckdbWorkerPool.release_all_main_db_handles(data_mgr)


    @staticmethod
    def reconnect_main_database(data_mgr: Any) -> None:
        DuckdbWorkerPool.resume_main_database(data_mgr)


    @staticmethod
    def release_worker_db_handles(data_mgr: Optional[Any] = None) -> None:
        """
        子进程 job 结束：关闭本进程 DuckDB，避免 pool shutdown 后仍占文件锁。

        业务方在 execute 的 finally 中调用；``data_mgr`` 为 None 时仅 reset DatabaseManager。
        """
        if mp.current_process().name == "MainProcess":
            return
        from core.infra.db.core.db_manager import DatabaseManager

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


    @staticmethod
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
        
        if not DuckdbWorkerPool.is_duckdb_backend(data_mgr):
            yield DuckdbWorkerPool.resolve_holder(data_mgr, allow_create=True)
            return

        dm = data_mgr if data_mgr is not None else DuckdbWorkerPool.resolve_holder(None)

        if DuckdbWorkerPool._main_suspend_depth > 0:
            DuckdbWorkerPool._main_suspend_depth += 1
            try:
                # 已 suspend 时禁止 allow_create：DataManager.__init__ 会 wait_for_main_end → 死锁。
                yield dm
            finally:
                DuckdbWorkerPool._main_suspend_depth -= 1
            return

        DuckdbWorkerPool.prepare_main_for_worker_pool(dm)
        DuckdbWorkerPool._main_suspend_depth = 1
        DuckdbWorkerPool._suspend_thread_ident = threading.get_ident()
        try:
            # 同样：suspend 之后不得新建会打开 DuckDB 的 holder。
            yield dm
        finally:
            DuckdbWorkerPool._finalize_worker_pool_main_process(
                dm,
                resume_main_after=resume_main_after,
                wait_children_timeout_sec=wait_children_timeout_sec,
            )


    @staticmethod
    @contextmanager
    def maybe_duckdb_worker_pool_scope(
        *,
        mode: DuckdbProcessPoolScopeMode = "auto",
        use_process_pool: bool,
        data_mgr: Optional[Any] = None,
        resume_main_after: bool = True,
    ) -> Iterator[Any]:
        """按 mode 决定是否进入 ``duckdb_worker_pool_main_process``。"""
        if not DuckdbWorkerPool.should_apply_process_pool_scope(
            mode=mode,
            use_process_pool=use_process_pool,
            data_mgr=data_mgr,
        ):
            yield DuckdbWorkerPool.resolve_holder(data_mgr, allow_create=True)
            return
        with DuckdbWorkerPool.duckdb_worker_pool_main_process(
            data_mgr,
            resume_main_after=resume_main_after,
        ) as dm:
            yield dm
