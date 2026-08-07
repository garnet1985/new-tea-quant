"""确定性伪随机（hash → [0, 1)）。

内部实现；公开入口 ``Utils.math.deterministic_unit_float``。
"""

from __future__ import annotations

import hashlib
from typing import Any


class DeterministicRandom:
    """由 key 派生可复现的单位区间伪随机数。"""

    @staticmethod
    def unit_float(*key_parts: Any) -> float:
        """
        由 ``key_parts`` 生成 ``[0, 1)`` 的确定性伪随机数。

        各 part 以 ``|`` 拼接后做 SHA-256，取 digest 前 8 个十六进制字符映射。
        """
        payload = "|".join(str(part) for part in key_parts)
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return int(digest[:8], 16) / float(0xFFFFFFFF)


__all__ = ["DeterministicRandom"]
