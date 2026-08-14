"""Pickle-safe helpers for BE __performance__ worker DB overlay.

ProcessPool spawn re-imports this module by name; publish overlay via
``Db.duckdb.worker_pool.install_config_overlay`` so workers inherit the
perf DuckDB paths or MySQL/PgSQL temp database (not userspace business DB).
"""
from __future__ import annotations

from typing import Any, Dict


def install_perf_worker_db_overlay(paths: Dict[str, str]) -> None:
    """Point worker RO DuckDB bootstrap at perf files (spawn-safe via env)."""
    from core.infra.db import Db

    if not paths.get("data"):
        return
    cfg = Db.duckdb.overlay_domain_paths(
        data=paths.get("data"),
        tag=paths.get("tag"),
        strategy=paths.get("strategy"),
    )
    Db.duckdb.worker_pool.install_config_overlay(cfg)


def install_perf_worker_server_overlay(cfg: Dict[str, Any]) -> None:
    """Point workers at a temp MySQL/PgSQL database (full config overlay)."""
    if not cfg:
        return
    from core.infra.db import Db

    Db.duckdb.worker_pool.install_config_overlay(cfg)
