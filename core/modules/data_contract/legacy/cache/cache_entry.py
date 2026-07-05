#!/usr/bin/env python3
"""单条 contract 缓存条目（不含 level：由落在哪个 Store 区分）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class ContractCacheEntry:
    """
    - ``meta``：失效与调试信息（如时序 ``start``/``end``、params 摘要）。
    - ``data``：物化结果（如 rows）。
    """

    meta: Dict[str, Any] = field(default_factory=dict)
    data: Any = None
