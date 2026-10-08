from core.infra.setup.core.step_errors import (
    DUCKDB_PROCESS_LOCK_MESSAGE,
    is_duckdb_process_lock,
    setup_failure_message,
)


def test_lock_message_replaces_duckdb_conflict() -> None:
    raw = (
        "Traceback (most recent call last):\n"
        "IO Error: Could not set lock on file data.duckdb: "
        "Conflicting lock is held in python.exe (PID 1)\n"
    )
    assert is_duckdb_process_lock(raw) is True
    assert setup_failure_message(raw) == DUCKDB_PROCESS_LOCK_MESSAGE


def test_lock_message_matches_chinese_wrapper() -> None:
    raw = "无法打开 DuckDB（文件被其他进程占用）: C:/data.duckdb"
    assert setup_failure_message(raw) == DUCKDB_PROCESS_LOCK_MESSAGE


def test_other_failures_keep_tail() -> None:
    raw = "x" * 700 + "部分表导入失败"
    out = setup_failure_message(raw, fallback_limit=20)
    assert out.endswith("部分表导入失败")
    assert len(out) == 20
    assert "lock" not in out.lower()


def test_empty_failure_is_empty() -> None:
    assert setup_failure_message("  ") == ""
    assert is_duckdb_process_lock("") is False
