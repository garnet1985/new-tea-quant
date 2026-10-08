"""把安装步骤的原始报错收成用户能直接看懂的句子。"""

from __future__ import annotations

DUCKDB_PROCESS_LOCK_MESSAGE = (
    "系统发现 DuckDB 正在被别的程序使用，请退出其他程序后继续尝试导入数据。"
)

_LOCK_TOKENS = (
    "conflicting lock",
    "could not set lock",
    "file is already open",
    "already open in",
    "文件被其他进程占用",
)


def is_duckdb_process_lock(text: str) -> bool:
    lower = str(text or "").lower()
    return any(token in lower for token in _LOCK_TOKENS)


def setup_failure_message(text: str, *, fallback_limit: int = 600) -> str:
    """锁冲突返回固定说明；其他失败保留原文末尾，避免整段 traceback。"""
    raw = str(text or "").strip()
    if not raw:
        return ""
    if is_duckdb_process_lock(raw):
        return DUCKDB_PROCESS_LOCK_MESSAGE
    limit = max(1, int(fallback_limit))
    return raw[-limit:]
