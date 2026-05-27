#!/usr/bin/env python3
"""成交量参与率约束：单笔成交不超过当日成交量的一定比例（volume 单位为股）。"""

from __future__ import annotations

from typing import Any, Dict, Literal, Optional, Tuple

ParticipationOnExceed = Literal["skip", "clip"]

_SKIP = "participation_skip"
_CLIP_ZERO = "participation_clip_zero"
_CLIPPED = "participation_clipped"


def parse_participation_on_exceed(raw: Any) -> ParticipationOnExceed:
    key = str(raw or "clip").strip().lower()
    if key in ("skip", "clip"):
        return key  # type: ignore[return-value]
    raise ValueError(
        f"participation_on_exceed 非法: {raw!r}；允许 skip | clip"
    )


def parse_max_participation_rate(raw: Any, *, default: float = 0.1) -> float:
    if raw is None or raw == "":
        return float(default)
    try:
        rate = float(raw)
    except (TypeError, ValueError) as e:
        raise ValueError("max_participation_rate 须为 (0, 1] 内数字") from e
    if rate <= 0.0 or rate > 1.0:
        raise ValueError("max_participation_rate 须在 (0, 1] 内；1 表示不限制")
    return rate


def bar_volume_shares(bar: Optional[Dict[str, Any]]) -> Optional[float]:
    """从 K 线 bar 读取成交量（股）。"""
    if not bar:
        return None
    raw = bar.get("volume")
    if raw is None or raw == "":
        return None
    try:
        vol = float(raw)
    except (TypeError, ValueError):
        return None
    if vol <= 0:
        return None
    return vol


def row_buy_bar_volume(row: Dict[str, Any]) -> Optional[float]:
    raw = row.get("buy_bar_volume")
    if raw is None or raw == "":
        return None
    try:
        vol = float(raw)
    except (TypeError, ValueError):
        return None
    return vol if vol > 0 else None


def row_sell_bar_volume(target_or_row: Dict[str, Any]) -> Optional[float]:
    raw = target_or_row.get("sell_bar_volume")
    if raw is None or raw == "":
        return None
    try:
        vol = float(raw)
    except (TypeError, ValueError):
        return None
    return vol if vol > 0 else None


def max_shares_by_participation(
    bar_volume: Optional[float],
    max_participation_rate: float,
) -> Optional[int]:
    """``None`` 表示不限制；``0`` 表示当日无可成交额度。

    缺少 ``bar_volume`` 时返回 ``None``（无法评估参与率，不阻断成交）。
    """
    if max_participation_rate >= 1.0 - 1e-12:
        return None
    if bar_volume is None:
        return None
    if bar_volume <= 0:
        return 0
    return int(bar_volume * max_participation_rate)


def apply_participation_to_shares(
    planned_shares: int,
    *,
    bar_volume: Optional[float],
    max_participation_rate: float,
    on_exceed: ParticipationOnExceed,
    floor_shares_fn,
    stock_id: str,
) -> Tuple[int, Optional[str]]:
    """
    返回 (最终股数, 结果标记)。

    - ``participation_skip``：skip 模式或缩量后不足最小交易单位
    - ``participation_clip_zero``：同 skip（计数可合并）
    - ``participation_clipped``：clip 后成交但少于计划
  - ``None``：未触发限制或计划已在限额内
    """
    planned = max(int(planned_shares or 0), 0)
    if planned <= 0:
        return 0, None

    cap = max_shares_by_participation(bar_volume, max_participation_rate)
    if cap is None:
        return planned, None
    if cap <= 0:
        return 0, _SKIP

    if planned <= cap:
        floored = int(floor_shares_fn(planned, stock_id))
        if floored <= 0:
            return 0, _SKIP
        return floored, None

    if on_exceed == "skip":
        return 0, _SKIP

    clipped = int(floor_shares_fn(cap, stock_id))
    if clipped <= 0:
        return 0, _CLIP_ZERO
    if clipped < planned:
        return clipped, _CLIPPED
    return clipped, None


__all__ = [
    "ParticipationOnExceed",
    "apply_participation_to_shares",
    "bar_volume_shares",
    "max_shares_by_participation",
    "parse_max_participation_rate",
    "parse_participation_on_exceed",
    "row_buy_bar_volume",
    "row_sell_bar_volume",
]
