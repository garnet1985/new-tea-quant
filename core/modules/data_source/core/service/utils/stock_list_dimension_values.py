"""从 stock_list 映射记录中收集板块/交易所/行业/地域维度值（纯函数，无 DB）。"""
from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple


def group_stock_list_dimension_values(
    raw_records: List[Dict[str, Any]],
) -> Tuple[List[str], List[str], List[str], List[str]]:
    """返回 ``(boards, markets, industries, areas)``，各为去重后的非空字符串列表。"""
    boards: Set[str] = set()
    markets: Set[str] = set()
    industries: Set[str] = set()
    areas: Set[str] = set()
    for record in raw_records:
        for key, target in (
            ("board", boards),
            ("market", markets),
            ("industry", industries),
            ("area", areas),
        ):
            v = (record.get(key) or "").strip()
            if v:
                target.add(v)
    return list(boards), list(markets), list(industries), list(areas)
