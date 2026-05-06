"""枚举器适配器：枚举摘要在进入 Simulator Res DB 快照写入路径前的轻量整形（无 Flask / 无表访问）。"""

from __future__ import annotations

from typing import Any, Dict


def sanitize_enum_payload_for_snapshot(payload: Dict[str, Any]) -> Dict[str, Any]:
    """浅拷贝并去掉值为 ``None`` 的顶层键，便于 JSON 落库。"""
    raw = dict(payload or {})
    return {k: v for k, v in raw.items() if v is not None}


__all__ = ["sanitize_enum_payload_for_snapshot"]
