#!/usr/bin/env python3
"""解析 amplitude_limit 的 default_risk / rules[].risk（st、star_st）。"""

from __future__ import annotations

from typing import Any, Dict, FrozenSet, Mapping, Optional, Sequence

RISK_TAGS = ("star_st", "st")


def parse_risk_ratio_map(raw: Any) -> Dict[str, float]:
    if not isinstance(raw, dict):
        return {}
    out: Dict[str, float] = {}
    for tag in RISK_TAGS:
        block = raw.get(tag)
        if not isinstance(block, dict):
            continue
        try:
            out[tag] = float(block.get("ratio"))
        except (TypeError, ValueError):
            continue
    return out


def normalize_status_tags(tags: Optional[Sequence[str]]) -> FrozenSet[str]:
    if not tags:
        return frozenset()
    return frozenset(str(t or "").strip().lower() for t in tags if str(t or "").strip())


def resolve_ratio_with_risk(
    base_ratio: float,
    risk_map: Mapping[str, float],
    status_tags: Optional[Sequence[str]],
) -> float:
    """``star_st`` 优先于 ``st``；无匹配标签则返回 ``base_ratio``。"""
    active = normalize_status_tags(status_tags)
    if not active or not risk_map:
        return base_ratio
    if "star_st" in active and "star_st" in risk_map:
        return float(risk_map["star_st"])
    if "st" in active and "st" in risk_map:
        return float(risk_map["st"])
    return base_ratio


__all__ = [
    "RISK_TAGS",
    "normalize_status_tags",
    "parse_risk_ratio_map",
    "resolve_ratio_with_risk",
]
