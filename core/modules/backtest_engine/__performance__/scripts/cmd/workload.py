"""Pickle-safe helpers for BE __performance__ worker DuckDB overlay.

ProcessPool spawn re-imports this module by name; keep overlay install here
so workers inherit the fake DuckDB paths (not userspace business DB).
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Optional

_PERF_OVERLAY_CFG: Optional[Dict[str, Any]] = None
_ORIG_DB_CFG_RO = None


def _perf_database_config_read_only() -> Dict[str, Any]:
    global _PERF_OVERLAY_CFG, _ORIG_DB_CFG_RO
    if _PERF_OVERLAY_CFG is not None:
        cfg = deepcopy(_PERF_OVERLAY_CFG)
        duck = cfg.setdefault("duckdb", {})
        domains = duck.setdefault("domains", {})
        if isinstance(domains, dict):
            for block in domains.values():
                if isinstance(block, dict):
                    block["read_only"] = True
        return cfg
    if _ORIG_DB_CFG_RO is not None:
        return _ORIG_DB_CFG_RO()
    from core.infra.db.core.engines.duckdb import process_pool_scope as pps

    return pps.database_config_read_only()


def install_perf_worker_db_overlay(paths: Dict[str, str]) -> None:
    """Point worker RO DuckDB bootstrap at perf files (spawn-safe via env)."""
    import json
    import os

    from core.infra.db import Db
    from core.infra.db.core.engines.duckdb import process_pool_scope as pps
    from core.infra.db.core.engines.duckdb.process_pool_scope import (
        _ENV_DUCKDB_CONFIG_JSON,
    )

    global _PERF_OVERLAY_CFG, _ORIG_DB_CFG_RO
    if not paths.get("data"):
        return
    _PERF_OVERLAY_CFG = Db.duckdb.overlay_domain_paths(
        data=paths.get("data"),
        tag=paths.get("tag"),
        strategy=paths.get("strategy"),
    )
    os.environ[_ENV_DUCKDB_CONFIG_JSON] = json.dumps(
        _PERF_OVERLAY_CFG, ensure_ascii=False
    )
    if _ORIG_DB_CFG_RO is None:
        _ORIG_DB_CFG_RO = pps.database_config_read_only
    pps.database_config_read_only = _perf_database_config_read_only  # type: ignore[assignment]
