#!/usr/bin/env python3
"""matching.id.start_with 等股票代码匹配。"""

from __future__ import annotations

from typing import Any, Dict, List


def extract_stock_code(stock_id: str) -> str:
    """``000001.SZ`` / ``600519.SH`` → 数字代码部分。"""
    raw = str(stock_id or "").strip().upper()
    if not raw:
        return ""
    head = raw.split(".", 1)[0]
    return "".join(ch for ch in head if ch.isdigit())


def _match_id_block(code: str, id_block: Dict[str, Any]) -> bool:
    prefixes_raw = id_block.get("start_with")
    if not isinstance(prefixes_raw, list):
        return False
    prefixes: List[str] = [str(p).strip() for p in prefixes_raw if str(p).strip()]
    if not prefixes or not code:
        return False

    hits = [code.startswith(p) for p in prefixes]
    relation = str(id_block.get("relation") or "or").strip().lower()
    if relation == "and":
        return all(hits)
    return any(hits)


def match_stock_id(stock_id: str, matching: Dict[str, Any]) -> bool:
    """
    是否命中 ``matching`` 配置。

    当前支持 ``matching.id.start_with``（多条前缀默认 OR，``relation: and`` 可选）。
    """
    if not isinstance(matching, dict) or not matching:
        return False
    id_block = matching.get("id")
    if not isinstance(id_block, dict):
        return False
    code = extract_stock_code(stock_id)
    return _match_id_block(code, id_block)


__all__ = ["extract_stock_code", "match_stock_id"]
