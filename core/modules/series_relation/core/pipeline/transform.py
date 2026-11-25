"""点列变换（returns 等）。"""

from __future__ import annotations

from typing import List, Tuple


def apply_transform(
    points: List[Tuple[str, float]],
    transform: str,
) -> List[Tuple[str, float]]:
    mode = str(transform or "none").strip() or "none"
    if mode == "none":
        return list(points)
    if mode == "returns":
        return _to_simple_returns(points)
    raise ValueError(f"未知 transform: {transform}")


def _to_simple_returns(points: List[Tuple[str, float]]) -> List[Tuple[str, float]]:
    if len(points) < 2:
        return []
    out: List[Tuple[str, float]] = []
    prev_date, prev_val = points[0]
    _ = prev_date
    for date, value in points[1:]:
        if prev_val == 0:
            prev_val = value
            continue
        out.append((date, (value - prev_val) / prev_val))
        prev_val = value
    return out


__all__ = ["apply_transform"]
