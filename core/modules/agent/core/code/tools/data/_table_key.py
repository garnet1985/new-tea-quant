"""Agent 信道侧：仅保留参数形状检查（域逻辑在 DataManager）。"""

from __future__ import annotations

from typing import Any, Dict, Set


def parse_table_key(
    arguments: Dict[str, Any], *, only: Set[str]
) -> str | Dict[str, Any]:
    """取出 key 字符串；合法性由 DataManager 判定。"""
    if set(arguments) != only:
        names = "、".join(sorted(only))
        return {"ok": False, "error": f"只接受参数 {names}"}
    key = arguments.get("key")
    if not isinstance(key, str) or not key.strip():
        return {"ok": False, "error": "key 不能为空"}
    return key.strip().strip("/")
