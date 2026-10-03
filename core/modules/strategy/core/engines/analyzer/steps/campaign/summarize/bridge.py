"""层间衔接句：报告头一句上游规模（展示层，不另起战役）。"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from . import value_ladders as ladders


def upstream_bridge(
    gathered: Optional[Mapping[str, Any]],
    *,
    layer: str,
) -> str:
    rows = ladders.ready_rows(gathered, layer=layer)
    baseline = ladders.baseline_row(rows)
    layers = (
        baseline.get("layers")
        if isinstance(baseline, Mapping) and isinstance(baseline.get("layers"), dict)
        else {}
    )
    enum = layers.get("enumerate") if isinstance(layers.get("enumerate"), dict) else {}
    price = (
        layers.get("price_factor")
        if isinstance(layers.get("price_factor"), dict)
        else {}
    )

    if layer == "enumerate":
        opp = _fmt_int(enum.get("total_opportunities"))
        if opp:
            return (
                f"当前配置纸面机会约 {opp} 笔（含重叠）；"
                "本层只看机会数量/分布与纸面出场结构，不是去噪账，也不是组合资金。"
            )
        return (
            "本层只看机会数量/分布与纸面出场结构；"
            "不是去噪账，也不是组合资金。"
        )

    if layer == "price_factor":
        opp = _fmt_int(enum.get("total_opportunities"))
        done = _fmt_int(
            price.get("total_completed_investments")
            if price.get("total_completed_investments") is not None
            else price.get("n_completed")
        )
        bits = []
        if opp:
            bits.append(f"枚举机会约 {opp} 笔")
        if done:
            bits.append(f"去噪后代表完成笔约 {done}")
        if bits:
            return (
                "本层基于"
                + "，".join(bits)
                + "；回答等权投一笔能不能赚。详见上一层枚举报告。"
            )
        return "本层基于去噪后的代表机会等权账；详见上一层枚举报告。"

    if layer == "portfolio":
        done = _fmt_int(
            price.get("total_completed_investments")
            if price.get("total_completed_investments") is not None
            else price.get("n_completed")
        )
        if done:
            return (
                f"本层基于价格完成笔约 {done}，看槽位/权重/分配如何改变账户结果；"
                "详见上一层价格报告。"
            )
        return "本层看资金分配如何改变账户结果；详见上一层价格报告。"

    return ""


def _fmt_int(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ""
    if number != number:  # NaN
        return ""
    return str(int(round(number)))


__all__ = ["upstream_bridge"]
