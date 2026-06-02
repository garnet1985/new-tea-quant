"""
DuckDB WAL 策略：尽量缩短 .wal 存在时间。

- 连接时设置 wal_autocheckpoint（按 WAL 体积自动 CHECKPOINT）
- 批量 renew 写入后、SIGINT、close() 时显式 CHECKPOINT
"""
from __future__ import annotations

import logging
import signal
import threading
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.infra.db.connection_management.connection_manager import ConnectionManager

logger = logging.getLogger(__name__)

_sigint_installed = False
_sigint_lock = threading.Lock()


def duckdb_shared_config(db_config: Dict[str, Any]) -> Dict[str, Any]:
    """duckdb 块内除 domains 外的共享项。"""
    duck = dict(db_config.get("duckdb") or {})
    return {k: v for k, v in duck.items() if k != "domains"}


def apply_connect_settings(conn: Any, adapter_config: Dict[str, Any]) -> None:
    """连接建立后设置 WAL 自动 checkpoint 阈值。"""
    wal_ac = adapter_config.get("wal_autocheckpoint")
    if wal_ac is None:
        wal_ac = "4MB"
    if wal_ac is False or wal_ac == "":
        return
    try:
        conn.execute(f"SET wal_autocheckpoint = '{_sql_string_literal(wal_ac)}'")
    except Exception as e:
        logger.debug("SET wal_autocheckpoint 跳过: %s", e)


def checkpoint_connection_manager(
    connection_manager: ConnectionManager,
    *,
    domains: Optional[list] = None,
) -> Dict[str, bool]:
    """
    对 DuckDB 各域执行 CHECKPOINT（无 .wal 或已合并则无副作用）。

    Returns:
        {domain: True 成功 / False 失败}
    """
    results: Dict[str, bool] = {}
    if not getattr(connection_manager, "is_duckdb", False):
        return results
    adapters = getattr(connection_manager, "domain_adapters", None) or {}
    targets = domains if domains is not None else sorted(adapters.keys())
    for domain in targets:
        adapter = adapters.get(domain)
        if adapter is None:
            continue
        if bool(getattr(adapter, "config", {}).get("read_only", False)):
            continue
        try:
            adapter.checkpoint()
            results[str(domain)] = True
        except Exception as e:
            logger.warning("DuckDB CHECKPOINT 失败 domain=%s: %s", domain, e)
            results[str(domain)] = False
    return results


def should_checkpoint_after_batch(db_config: Dict[str, Any]) -> bool:
    return bool(duckdb_shared_config(db_config).get("checkpoint_after_batch_save", True))


def should_checkpoint_after_persist(db_config: Dict[str, Any]) -> bool:
    return bool(duckdb_shared_config(db_config).get("checkpoint_after_persist", False))


def should_checkpoint_on_sigint(db_config: Dict[str, Any]) -> bool:
    return bool(duckdb_shared_config(db_config).get("checkpoint_on_sigint", True))


def should_checkpoint_after_tag_run(db_config: Dict[str, Any]) -> bool:
    return bool(duckdb_shared_config(db_config).get("checkpoint_after_tag_run", True))


def install_sigint_checkpoint_handler(
    connection_manager: ConnectionManager,
    db_config: Dict[str, Any],
) -> None:
    """主线程注册 SIGINT：合并 WAL 后再抛出 KeyboardInterrupt。"""
    global _sigint_installed
    if not should_checkpoint_on_sigint(db_config):
        return
    if threading.current_thread() is not threading.main_thread():
        return
    with _sigint_lock:
        if _sigint_installed:
            return

        def _handler(signum, frame):
            logger.info("收到 Ctrl+C，正在将 DuckDB WAL 合并进主库…")
            try:
                checkpoint_connection_manager(connection_manager)
            except Exception as e:
                logger.warning("中断时 CHECKPOINT 未完全成功（下次独占打开仍会回放 WAL）: %s", e)
            signal.signal(signal.SIGINT, signal.SIG_DFL)
            raise KeyboardInterrupt

        signal.signal(signal.SIGINT, _handler)
        _sigint_installed = True


def _sql_string_literal(value: Any) -> str:
    return str(value).replace("'", "''")
