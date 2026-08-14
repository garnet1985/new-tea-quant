"""
DuckDB WAL 策略：尽量缩短 .wal 存在时间。

- 连接时设置 wal_autocheckpoint（按 WAL 体积自动 CHECKPOINT）
- 批量 renew 写入后、SIGINT、close() 时显式 CHECKPOINT
"""
from __future__ import annotations

import logging
import signal
import threading
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class DuckdbWalPolicy:
    """DuckDB WAL / CHECKPOINT 策略（公开入口 Db.duckdb.wal）。"""

    _sigint_installed = False
    _sigint_lock = threading.Lock()

    @staticmethod
    def shared_config(db_config: Dict[str, Any]) -> Dict[str, Any]:
        """duckdb 块内除 domains 外的共享项。"""
        duck = dict(db_config.get("duckdb") or {})
        return {k: v for k, v in duck.items() if k != "domains"}

    @staticmethod
    def apply_connect_settings(conn: Any, adapter_config: Dict[str, Any]) -> None:
        """连接建立后设置 WAL 自动 checkpoint 阈值；SET 失败直接抛出。"""
        wal_ac = adapter_config.get("wal_autocheckpoint")
        if wal_ac is None:
            wal_ac = "4MB"
        if wal_ac is False or wal_ac == "":
            return
        conn.execute(
            f"SET wal_autocheckpoint = '{DuckdbWalPolicy._sql_string_literal(wal_ac)}'"
        )

    @staticmethod
    def should_checkpoint_after_batch(db_config: Dict[str, Any]) -> bool:
        return bool(
            DuckdbWalPolicy.shared_config(db_config).get(
                "checkpoint_after_batch_save", True
            )
        )

    @staticmethod
    def should_checkpoint_after_persist(db_config: Dict[str, Any]) -> bool:
        return bool(
            DuckdbWalPolicy.shared_config(db_config).get(
                "checkpoint_after_persist", False
            )
        )

    @staticmethod
    def should_checkpoint_on_sigint(db_config: Dict[str, Any]) -> bool:
        return bool(
            DuckdbWalPolicy.shared_config(db_config).get("checkpoint_on_sigint", True)
        )

    @staticmethod
    def should_checkpoint_after_tag_run(db_config: Dict[str, Any]) -> bool:
        return bool(
            DuckdbWalPolicy.shared_config(db_config).get(
                "checkpoint_after_tag_run", True
            )
        )

    @staticmethod
    def checkpoint_engine(
        engine: Any,
        *,
        domains: Optional[list] = None,
    ) -> Dict[str, bool]:
        """对 DuckdbEngine 执行 CHECKPOINT。"""
        checkpoint = getattr(engine, "checkpoint", None)
        if not callable(checkpoint):
            raise TypeError(
                f"DuckdbWalPolicy.checkpoint_engine 需要带 checkpoint() 的 DuckdbEngine，"
                f"收到 {type(engine).__name__}"
            )
        return checkpoint(domains=domains)

    @staticmethod
    def install_sigint_checkpoint_handler(
        engine: Any,
        db_config: Dict[str, Any],
    ) -> None:
        """主线程 SIGINT：对 DuckdbEngine 合并 WAL。"""
        if not DuckdbWalPolicy.should_checkpoint_on_sigint(db_config):
            return
        if threading.current_thread() is not threading.main_thread():
            return
        with DuckdbWalPolicy._sigint_lock:
            if DuckdbWalPolicy._sigint_installed:
                return

            def _handler(signum, frame):
                from core.infra.db.core.engines.duckdb.process_pool_scope import (
                    DuckdbWorkerPool,
                )

                if DuckdbWorkerPool.is_main_duckdb_worker_pool_active():
                    logger.info(
                        "收到 Ctrl+C（ProcessPool 阶段），跳过 SIGINT CHECKPOINT，"
                        "由 worker finally 恢复主库后再合并 WAL"
                    )
                    signal.signal(signal.SIGINT, signal.SIG_DFL)
                    raise KeyboardInterrupt

                logger.info("收到 Ctrl+C，正在将 DuckDB WAL 合并进主库…")
                try:
                    if getattr(engine, "_initialized", False):
                        DuckdbWalPolicy.checkpoint_engine(engine)
                    else:
                        logger.info(
                            "主库 DuckDB 未连接（如 Tag stage_in_worker suspend），"
                            "跳过 SIGINT CHECKPOINT，由业务 finally 恢复后再合并 WAL"
                        )
                except Exception as e:
                    logger.warning("中断时 CHECKPOINT 未完全成功: %s", e)
                signal.signal(signal.SIGINT, signal.SIG_DFL)
                raise KeyboardInterrupt

            signal.signal(signal.SIGINT, _handler)
            DuckdbWalPolicy._sigint_installed = True

    @staticmethod
    def _sql_string_literal(value: Any) -> str:
        return str(value).replace("'", "''")
