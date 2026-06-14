"""
确定性伪随机（hash → [0, 1)）。

用于策略掷骰、可复现采样等需要 seed 稳定输出的场景。
"""

from __future__ import annotations

import hashlib
from typing import Any


def deterministic_unit_float(*key_parts: Any) -> float:
    """
    由 key_parts 生成 [0, 1) 的确定性伪随机数。

    各 part 以 ``|`` 拼接后做 SHA-256，取 digest 前 8 个十六进制字符映射到单位区间。
    例如 ``deterministic_unit_float(stock_id, as_of_date, seed)``。
    """
    payload = "|".join(str(part) for part in key_parts)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) / float(0xFFFFFFFF)


__all__ = ["deterministic_unit_float"]
