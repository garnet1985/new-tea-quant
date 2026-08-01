"""Shared database config defaults (app settings + setup wizard)."""

from __future__ import annotations

from typing import Dict

# Relative paths under userspace system DB directory.
DEFAULT_DUCKDB_DOMAINS: Dict[str, Dict[str, str]] = {
    "data": {"db_path": "data.duckdb"},
    "tag": {"db_path": "tag.duckdb"},
    "strategy": {"db_path": "strategy.duckdb"},
}

DUCKDB_DOMAIN_FILES = ("data.duckdb", "tag.duckdb", "strategy.duckdb")

SUPPORTED_DB_TYPES = ("postgresql", "mysql", "duckdb")
