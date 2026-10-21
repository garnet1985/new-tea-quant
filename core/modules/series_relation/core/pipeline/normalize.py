"""系列归一化。"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple


def normalize_points(
    points: Sequence[Tuple[str, float]],
    mode: str,
) -> List[Dict[str, object]]:
    """``points`` 为 ``(date, raw)``；返回带 ``raw``/``norm`` 的 dict 列表。"""
    if not points:
        return []
    values = [float(v) for _, v in points]
    norms = _norms(values, mode)
    out: List[Dict[str, object]] = []
    for (date, raw), norm in zip(points, norms):
        out.append({"date": date, "raw": float(raw), "norm": float(norm)})
    return out


def _norms(values: Sequence[float], mode: str) -> List[float]:
    name = str(mode or "none").strip() or "none"
    if name == "none":
        return [float(v) for v in values]
    if name == "zscore":
        mean = sum(values) / len(values)
        var = sum((v - mean) ** 2 for v in values) / len(values)
        std = math.sqrt(var)
        if std < 1e-12:
            return [0.0 for _ in values]
        return [(v - mean) / std for v in values]
    if name == "minmax":
        lo = min(values)
        hi = max(values)
        span = hi - lo
        if abs(span) < 1e-12:
            return [0.0 for _ in values]
        return [(v - lo) / span for v in values]
    if name == "index_100":
        base = values[0]
        if abs(base) < 1e-12:
            return [100.0 for _ in values]
        return [100.0 * v / base for v in values]
    return [float(v) for v in values]


__all__ = ["normalize_points"]
