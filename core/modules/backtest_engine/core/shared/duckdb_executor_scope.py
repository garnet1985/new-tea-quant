"""Shared DuckDB ProcessPool scope wrapper for backtest executors."""
from __future__ import annotations

import logging
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


def execute_with_duckdb_process_pool_scope(
    inner_execute: Callable[..., T],
    *,
    data_mgr: Any | None,
    duckdb_process_pool_scope: str,
    duckdb_resume_main_after_pool: bool,
    **inner_kwargs: Any,
) -> T:
    """Run *inner_execute* inside DuckDB worker pool scope when applicable."""
    from core.infra.db.core.engines.duckdb.process_pool_scope import (
        maybe_duckdb_worker_pool_scope,
        should_apply_process_pool_scope,
    )

    log_label = str(inner_kwargs.get("log_label", "执行"))
    use_scope = should_apply_process_pool_scope(
        mode=duckdb_process_pool_scope,  # type: ignore[arg-type]
        use_process_pool=True,
        data_mgr=data_mgr,
    )
    if use_scope:
        logger.info(
            "%s DuckDB ProcessPool scope enabled (mode=%s)",
            log_label,
            duckdb_process_pool_scope,
        )
    else:
        logger.debug(
            "%s DuckDB ProcessPool scope skipped (mode=%s)",
            log_label,
            duckdb_process_pool_scope,
        )

    with maybe_duckdb_worker_pool_scope(
        mode=duckdb_process_pool_scope,  # type: ignore[arg-type]
        use_process_pool=True,
        data_mgr=data_mgr,
        resume_main_after=duckdb_resume_main_after_pool,
    ):
        return inner_execute(**inner_kwargs)


__all__ = ["execute_with_duckdb_process_pool_scope"]
