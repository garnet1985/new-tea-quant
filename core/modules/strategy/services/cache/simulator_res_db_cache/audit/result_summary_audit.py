#!/usr/bin/env python3
"""
``result_summary`` JSON 内记录行级写次数，用于「单行复写超过 n 次则删行」(见 ``docs/db-cache-service.md`` §7)。

元数据键与业务键隔离，避免与 enum/price/capital 冲突。
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

# 与 product 约定：元数据放在该键下
META_KEY = "_db_cache_meta"


def read_write_count(result_summary: Dict[str, Any]) -> int:
    raw = (result_summary or {}).get(META_KEY)
    if not isinstance(raw, dict):
        return 0
    try:
        return max(0, int(raw.get("write_count") or 0))
    except (TypeError, ValueError):
        return 0


def with_initial_write_count(result_summary: Dict[str, Any]) -> Dict[str, Any]:
    """新建快照行时：第一次落库计为第 1 次写入。"""
    out = dict(result_summary or {})
    out[META_KEY] = {"write_count": 1}
    return out


def merge_for_update(
    previous_summary: Dict[str, Any],
    incoming_summary: Dict[str, Any],
    *,
    max_writes: int,
) -> Tuple[Dict[str, Any], str]:
    """
    在 ``previous`` 上合并 ``incoming``（浅合并顶层键），并将 ``write_count`` 设为 ``previous_count + 1``。

    Returns:
        ``(merged_summary, outcome)``
        - ``outcome == "ok"`` — 应执行 UPDATE；
        - ``outcome == "delete"`` — 已超过 ``max_writes``，应 DELETE 该行且不 UPDATE。
    """
    prev = dict(previous_summary or {})
    merged = dict(prev)
    merged.update(dict(incoming_summary or {}))
    merged.pop(META_KEY, None)
    prev_count = read_write_count(prev)
    next_count = prev_count + 1
    merged[META_KEY] = {"write_count": next_count}
    if next_count > max_writes:
        return merged, "delete"
    return merged, "ok"


__all__ = ["META_KEY", "merge_for_update", "read_write_count", "with_initial_write_count"]
