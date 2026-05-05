#!/usr/bin/env python3
"""``result_report`` 聚合：三步模拟器各自一份摘要 dict，可部分为空。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional


@dataclass
class ReportSnapshot:
    """
    内存态报告快照；写入库表 ``result_report`` JSON 时用 ``to_dict()``。

    三个槽位对应枚举 / 价格 / 资金回测；产生一次缓存只填其中一个即可，其余保持 ``None``。
    落库 JSON 键：``"enum"``、``"price_factor"``、``"capital_allocation"``。
    """

    enum: Optional[Dict[str, Any]] = None
    price: Optional[Dict[str, Any]] = None
    capital: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """供持久化或合并进表列：仅包含已设置的槽位（跳过 ``None``）。"""
        out: Dict[str, Any] = {}
        if self.enum is not None:
            out["enum"] = dict(self.enum)
        if self.price is not None:
            out["price_factor"] = dict(self.price)
        if self.capital is not None:
            out["capital_allocation"] = dict(self.capital)
        return out

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any] | None) -> ReportSnapshot:
        """从表列或 API dict 还原（识别 ``enum`` / ``price_factor`` / ``capital_allocation``）。"""
        if not raw:
            return cls()
        r = dict(raw)
        enum_v = r.get("enum")
        price_v = r.get("price_factor")
        cap_v = r.get("capital_allocation")
        return cls(
            enum=dict(enum_v) if isinstance(enum_v, dict) else None,
            price=dict(price_v) if isinstance(price_v, dict) else None,
            capital=dict(cap_v) if isinstance(cap_v, dict) else None,
        )


__all__ = ["ReportSnapshot"]
