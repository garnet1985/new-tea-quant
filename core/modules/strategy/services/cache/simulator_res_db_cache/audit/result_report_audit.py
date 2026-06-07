#!/usr/bin/env python3
"""``result_report`` JSON 内 ``_db_cache_meta.write_count`` 审计。"""

from __future__ import annotations

from typing import Any, Dict, Tuple

DB_CACHE_META_KEY = "_db_cache_meta"
WRITE_COUNT_KEY = "write_count"


def strip_db_cache_meta(report: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(report or {})
    out.pop(DB_CACHE_META_KEY, None)
    return out


def get_write_count(report: Dict[str, Any]) -> int:
    meta = (report or {}).get(DB_CACHE_META_KEY)
    if not isinstance(meta, dict):
        return 0
    try:
        return int(meta.get(WRITE_COUNT_KEY, 0) or 0)
    except (TypeError, ValueError):
        return 0


def attach_initial_write_meta(report: Dict[str, Any]) -> Dict[str, Any]:
    merged = strip_db_cache_meta(dict(report or {}))
    merged[DB_CACHE_META_KEY] = {WRITE_COUNT_KEY: 1}
    return merged


def bump_write_count(report: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    merged = dict(report or {})
    meta = dict(merged.get(DB_CACHE_META_KEY) or {})
    try:
        count = int(meta.get(WRITE_COUNT_KEY, 0) or 0) + 1
    except (TypeError, ValueError):
        count = 1
    meta[WRITE_COUNT_KEY] = count
    merged[DB_CACHE_META_KEY] = meta
    return merged, count


__all__ = [
    "DB_CACHE_META_KEY",
    "WRITE_COUNT_KEY",
    "attach_initial_write_meta",
    "bump_write_count",
    "get_write_count",
    "strip_db_cache_meta",
]
