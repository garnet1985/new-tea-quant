"""战役指标读写：delta / 层数值，供 attribute / effects / summarize / present 共用。"""
from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

from core.modules.analysis import Analysis

READY = frozenset({"hit", "simulated"})


def layer_number(
    layers: Mapping[str, Any],
    layer: str,
    outcome: str,
) -> Optional[float]:
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
    return part_value(item.get("deltas") or [], layer, outcome, field="delta")


def outcome_value(
    parts: Sequence[Any],
    layer: str,
    outcome: str,
) -> Optional[float]:
    return part_value(parts, layer, outcome, field="value")
