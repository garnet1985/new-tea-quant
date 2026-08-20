"""
DuckDB WAL 策略：尽量缩短 .wal 存在时间。

- 连接时设置 wal_autocheckpoint（按 WAL 体积自动 CHECKPOINT）
- 批量 renew 写入后、close() 时显式 CHECKPOINT
- SIGINT 不再 CHECKPOINT（会与进行中的查询/进程池死锁）；由 process_cleanup 强制退出
"""
from __future__ import annotations

import threading
from typing import Any, Dict, Optional


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
        """主线程 SIGINT：立刻杀掉子进程并退出。

        禁止在 handler 里 CHECKPOINT：工作台回测线程若正占用 DuckDB，
        CHECKPOINT 会与查询死锁，Windows 上 Ctrl+C 表现为无法退出。
        WAL 由下次打开主库时恢复。``engine`` / ``checkpoint_on_sigint``
        保留签名兼容；中断路径不再读它们。
        """
        _ = engine
        _ = db_config
        if threading.current_thread() is not threading.main_thread():
            return
        with DuckdbWalPolicy._sigint_lock:
            if DuckdbWalPolicy._sigint_installed:
                return
            from core.ui.process_cleanup import install_interrupt_force_exit

            install_interrupt_force_exit()
            DuckdbWalPolicy._sigint_installed = True

    @staticmethod
    def _sql_string_literal(value: Any) -> str:
        return str(value).replace("'", "''")
