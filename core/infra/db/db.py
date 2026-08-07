"""Db 门面（Facade）— infra.db 对外统一入口类。

实现位于 ``core/``；跨模块契约类型见 ``contracts.py``。
公开能力一律挂在本类命名空间上，不导出游离函数。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterator, Optional, Tuple

from core.infra.db.core.db_manager import DatabaseManager
from core.infra.db.core.engines.factory import EngineFactory
from core.infra.db.core.engines.meta import EngineConfigMeta
from core.infra.db.core.migrate_manager import MigrationManager


class ManagerNamespace:
    """数据库管理器命名空间（对应 DatabaseManager）。"""

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

    @staticmethod
    def default_snapshot_path(repo_root: Path) -> Path:
        return MigrationManager.default_snapshot_path(repo_root)

    @staticmethod
    def build_plan(*args: Any, **kwargs: Any):
        return MigrationManager.build_plan(*args, **kwargs)

    @staticmethod
    def run(*args: Any, **kwargs: Any):
        return MigrationManager.run(*args, **kwargs)

    @staticmethod
    def apply(pre_mirror_snapshot: Path, **kwargs: Any):
        """执行迁移（``MigrationManager.run(..., apply=True)``）。"""
        kwargs.setdefault("apply", True)
        return MigrationManager.run(pre_mirror_snapshot, **kwargs)


class EngineNamespace:
    """Engine 配置元信息与工厂。"""

    @staticmethod
    def build_meta(
        raw_config: Dict[str, Any], *, is_verbose: bool = False
    ) -> EngineConfigMeta:
        return EngineConfigMeta.from_raw_config(raw_config, is_verbose=is_verbose)

    @staticmethod
    def create(meta: EngineConfigMeta):
        return EngineFactory.create(meta)


class DuckdbWorkerPoolNamespace:
    """DuckDB 多进程 worker 池协作（主进程释放 / 恢复文件锁）。"""

    CONFIG_OVERLAY_ENV = "NTQ_DATABASE_CONFIG_JSON"

    @staticmethod
    def is_backend(data_mgr: Any = None) -> bool:
        from core.infra.db.core.engines.duckdb.process_pool_scope import DuckdbWorkerPool

        return DuckdbWorkerPool.is_duckdb_backend(data_mgr)

    @staticmethod
    def install_config_overlay(cfg: Dict[str, Any]) -> None:
        """Publish database config overlay via env (spawn-safe; no monkeypatch)."""
        from core.infra.db.core.engines.duckdb.process_pool_scope import DuckdbWorkerPool

        DuckdbWorkerPool.install_config_overlay(cfg)

    @staticmethod
    def should_apply(
        *,
        mode: Any,
        use_process_pool: bool,
        data_mgr: Optional[Any] = None,
    ) -> bool:
        from core.infra.db.core.engines.duckdb.process_pool_scope import DuckdbWorkerPool

        return DuckdbWorkerPool.should_apply_process_pool_scope(
            mode=mode, use_process_pool=use_process_pool, data_mgr=data_mgr
        )

    @staticmethod
    def prepare_main(data_mgr: Any = None) -> None:
        from core.infra.db.core.engines.duckdb.process_pool_scope import DuckdbWorkerPool

        DuckdbWorkerPool.prepare_main_for_worker_pool(data_mgr)

    @staticmethod
    def restore_after() -> None:
        from core.infra.db.core.engines.duckdb.process_pool_scope import DuckdbWorkerPool

        DuckdbWorkerPool.restore_after_worker_pool()

    @staticmethod
    def maybe_scope(
        *,
        mode: Any = "auto",
        use_process_pool: bool,
        data_mgr: Optional[Any] = None,
        resume_main_after: bool = True,
    ) -> Iterator[Any]:
        from core.infra.db.core.engines.duckdb.process_pool_scope import DuckdbWorkerPool

        return DuckdbWorkerPool.maybe_duckdb_worker_pool_scope(
            mode=mode,
            use_process_pool=use_process_pool,
            data_mgr=data_mgr,
            resume_main_after=resume_main_after,
        )

    @staticmethod
    def main_process(
        data_mgr: Any = None,
        *,
        resume_main_after: bool = True,
        wait_children_timeout_sec: float = 30.0,
    ) -> Iterator[Any]:
        from core.infra.db.core.engines.duckdb.process_pool_scope import DuckdbWorkerPool

        return DuckdbWorkerPool.duckdb_worker_pool_main_process(
            data_mgr,
            resume_main_after=resume_main_after,
            wait_children_timeout_sec=wait_children_timeout_sec,
        )

    @staticmethod
    def recover_after_interrupt(data_mgr: Any = None) -> None:
        from core.infra.db.core.engines.duckdb.process_pool_scope import DuckdbWorkerPool

        DuckdbWorkerPool.recover_after_worker_pool_interrupt(data_mgr)

    @staticmethod
    def ensure_data_manager_restored(data_mgr: Any = None) -> Any:
        from core.infra.db.core.engines.duckdb.process_pool_scope import DuckdbWorkerPool

        return DuckdbWorkerPool.ensure_data_manager_restored(data_mgr)

    @staticmethod
    def wait_pool_children_done(*, timeout_sec: float = 15.0) -> None:
        from core.infra.db.core.engines.duckdb.process_pool_scope import DuckdbWorkerPool

        DuckdbWorkerPool.wait_pool_children_done(timeout_sec=timeout_sec)

    @staticmethod
    def wait_for_main_end(*, timeout_sec: float = 600.0) -> None:
        from core.infra.db.core.engines.duckdb.process_pool_scope import DuckdbWorkerPool

        DuckdbWorkerPool.wait_for_main_duckdb_worker_pool_end(timeout_sec=timeout_sec)

    @staticmethod
    def is_main_active() -> bool:
        from core.infra.db.core.engines.duckdb.process_pool_scope import DuckdbWorkerPool

        return DuckdbWorkerPool.is_main_duckdb_worker_pool_active()

    @staticmethod
    def connect_domains(
        db: Any, *, domains: Tuple[str, ...], read_only: bool
    ) -> None:
        from core.infra.db.core.engines.duckdb.process_pool_scope import DuckdbWorkerPool

        DuckdbWorkerPool.connect_duckdb_domains(db, domains=domains, read_only=read_only)

    @staticmethod
    def database_config_read_only() -> dict[str, Any]:
        from core.infra.db.core.engines.duckdb.process_pool_scope import DuckdbWorkerPool

        return DuckdbWorkerPool.database_config_read_only()

    @staticmethod
    def release_worker_db_handles(data_mgr: Optional[Any] = None) -> None:
        from core.infra.db.core.engines.duckdb.process_pool_scope import DuckdbWorkerPool

        DuckdbWorkerPool.release_worker_db_handles(data_mgr)

    @staticmethod
    def release_all_main_handles(data_mgr: Any) -> None:
        """关闭主进程全部 DuckDB 连接（spawn worker 前调用）。"""
        from core.infra.db.core.engines.duckdb.process_pool_scope import DuckdbWorkerPool

        DuckdbWorkerPool.release_all_main_db_handles(data_mgr)


class DuckdbWalNamespace:
    """DuckDB WAL / CHECKPOINT 策略。"""

    @staticmethod
    def should_checkpoint_after_batch(db_config: Dict[str, Any]) -> bool:
        from core.infra.db.core.engines.duckdb.wal_policy import DuckdbWalPolicy

        return DuckdbWalPolicy.should_checkpoint_after_batch(db_config)

    @staticmethod
    def should_checkpoint_after_persist(db_config: Dict[str, Any]) -> bool:
        from core.infra.db.core.engines.duckdb.wal_policy import DuckdbWalPolicy

        return DuckdbWalPolicy.should_checkpoint_after_persist(db_config)

    @staticmethod
    def should_checkpoint_on_sigint(db_config: Dict[str, Any]) -> bool:
        from core.infra.db.core.engines.duckdb.wal_policy import DuckdbWalPolicy

        return DuckdbWalPolicy.should_checkpoint_on_sigint(db_config)

    @staticmethod
    def should_checkpoint_after_tag_run(db_config: Dict[str, Any]) -> bool:
        from core.infra.db.core.engines.duckdb.wal_policy import DuckdbWalPolicy

        return DuckdbWalPolicy.should_checkpoint_after_tag_run(db_config)

    @staticmethod
    def checkpoint_engine(
        engine: Any, *, domains: Optional[list] = None
    ) -> Dict[str, bool]:
        from core.infra.db.core.engines.duckdb.wal_policy import DuckdbWalPolicy

        return DuckdbWalPolicy.checkpoint_engine(engine, domains=domains)

    @staticmethod
    def install_sigint_checkpoint_handler(
        engine: Any, db_config: Dict[str, Any]
    ) -> None:
        from core.infra.db.core.engines.duckdb.wal_policy import DuckdbWalPolicy

        DuckdbWalPolicy.install_sigint_checkpoint_handler(engine, db_config)


class DuckdbNamespace:
    """DuckDB 跨模块协作入口。"""

    worker_pool = DuckdbWorkerPoolNamespace
    wal = DuckdbWalNamespace

    @staticmethod
    def resolve_db_path(db_path: str) -> str:
        from core.infra.db.core.engines.duckdb.paths import resolve_duckdb_db_path

        return resolve_duckdb_db_path(db_path)

    @staticmethod
    def overlay_domain_paths(
        base_config: Optional[Dict[str, Any]] = None,
        *,
        data: Optional[str] = None,
        tag: Optional[str] = None,
        strategy: Optional[str] = None,
    ) -> Dict[str, Any]:
        """返回一份 database 配置副本，覆盖 DuckDB 各域 ``db_path``。

        相对路径仍按 ``resolve_db_path`` 解析到 ``userspace/system/db/``；
        **绝对路径**原样使用（性能套件可把库文件放在模块 ``__performance__/`` 下）。
        未传入的域保留 ``base_config`` / 默认配置中的值。
        """
        from copy import deepcopy

        from core.infra.project_context import ProjectContext

        if base_config is None:
            cfg: Dict[str, Any] = deepcopy(
                ProjectContext.config.load_database_config("duckdb")
            )
        else:
            cfg = deepcopy(dict(base_config))

        cfg["database_type"] = "duckdb"
        duck = cfg.setdefault("duckdb", {})
        if not isinstance(duck, dict):
            raise ValueError("database config.duckdb 必须是 object")
        domains = duck.setdefault("domains", {})
        if not isinstance(domains, dict):
            raise ValueError("database config.duckdb.domains 必须是 object")

        overlays = {"data": data, "tag": tag, "strategy": strategy}
        for domain, path in overlays.items():
            if path is None:
                continue
            block = domains.setdefault(domain, {})
            if not isinstance(block, dict):
                raise ValueError(f"duckdb.domains.{domain} 必须是 object")
            block["db_path"] = str(path)
        return cfg


class SqlNamespace:
    """跨后端 SQL 标识 / 表名辅助。"""

    @staticmethod
    def qualify_table_name(config: Dict[str, Any], logical_name: str) -> str:
        from core.infra.db.core.engines.shared.dialect import sql_qualify_table_name

        return sql_qualify_table_name(config, logical_name)


class RowsNamespace:
    """行数据规范化辅助。"""

    @staticmethod
    def clean_nan_in_list(
        data_list: list, default: Any = None
    ) -> list:
        from core.infra.db.core.engines.shared.row_sql import clean_nan_in_list

        return clean_nan_in_list(data_list, default=default)


class Db:
    """New Tea Quant（NTQ）数据库门面类（Facade：对外统一入口）。"""

    manager = ManagerNamespace
    migration = MigrationNamespace
    engine = EngineNamespace
    duckdb = DuckdbNamespace
    sql = SqlNamespace
    rows = RowsNamespace


__all__ = ["Db"]
