"""战役指标读写：差值和层数值，供归因、总结和展示共用。"""
from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

from core.modules.analysis import Analysis

READY = frozenset({"hit", "simulated"})


def layer_number(
    layers: Mapping[str, Any],
    layer: str,
    outcome: str,
) -> Optional[float]:
    """读取某一层的数值指标。"""
    block = layers.get(layer)
    if not isinstance(block, dict):
        return None
    return Analysis.Classical.coerce_float(block.get(outcome))


def part_value(
    parts: Sequence[Any],
    layer: str,
    outcome: str,
    *,
    field: str = "value",
) -> Optional[float]:
    """从分项列表里取出指定层和指标。"""
    for part in parts:
        if not isinstance(part, dict):
            continue
        if str(part.get("layer") or "") != layer:
            continue
        if str(part.get("outcome") or "") != outcome:
            continue
        return Analysis.Classical.coerce_float(part.get(field))
    return None


def item_delta(
    item: Mapping[str, Any],
    layer: str,
    outcome: str,
) -> Optional[float]:
    """读取一行相对基准的差值。"""
    return part_value(item.get("deltas") or [], layer, outcome, field="delta")


def outcome_value(
    parts: Sequence[Any],
    layer: str,
    outcome: str,
) -> Optional[float]:
    """读取分项里的结果值。"""
    return part_value(parts, layer, outcome, field="value")
