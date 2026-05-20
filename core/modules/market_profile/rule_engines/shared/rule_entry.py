#!/usr/bin/env python3
"""规则条目解析共用辅助。"""

from __future__ import annotations

from typing import Any, Dict


def max_matching_prefix_len(matching: Dict[str, Any]) -> int:
    """``matching.id.start_with`` 中最长前缀长度，用于例外规则排序。"""
    id_block = matching.get("id") if isinstance(matching, dict) else None
    if not isinstance(id_block, dict):
        return 0
    prefixes = id_block.get("start_with")
    if not isinstance(prefixes, list):
        return 0
    lengths = [len(str(p).strip()) for p in prefixes if str(p).strip()]
    return max(lengths) if lengths else 0


__all__ = ["max_matching_prefix_len"]
