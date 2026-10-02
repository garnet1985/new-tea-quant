"""把组合事实收成基本结论。不编反事实百分比，不讲门贡献。"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

_ROI_BIAS = 0.02
_LOW_UTIL_PCT = 40.0
_TOP5_CONCENTRATED_PCT = 50.0
_MIN_CONCENTRATION_N = 8
_GROUP_MIN_N = 3


class PortfolioConclude:
    """规则结论；一条 id 对应建议里的一条。"""

    @classmethod
    def run(cls, facts: Mapping[str, Any]) -> List[Dict[str, Any]]:
        fill = dict(facts.get("fill") or {})
        quality = dict(facts.get("taken_vs_leftover") or {})
        groups = list(facts.get("groups") or [])
        drawdown = dict(facts.get("drawdown") or {})
        out: List[Dict[str, Any]] = []
        out.extend(cls._availability(facts, fill))
        out.extend(cls._fill(fill, quality))
        out.extend(cls._quality(quality, fill))
        out.extend(cls._slots(fill))
        out.extend(cls._cash(fill))
        out.extend(cls._groups(groups))
        out.extend(cls._concentration(fill))
        out.extend(cls._drawdown(drawdown, fill))
        out.append(
            {
                "id": "not_price_edge",
                "text": "这是资金约束后的账户结果，不是价格层等权边。",
            }
        )
        return out

    @staticmethod
    def _availability(
        facts: Mapping[str, Any], fill: Mapping[str, Any]
    ) -> List[Dict[str, Any]]:
        if not facts.get("price_available"):
            return [
                {
                    "id": "no_price_contrast",
                    "text": "没有价格账本，买到 / 漏掉答不了。无差不能默认。",
                }
            ]
        if int(fill.get("price_completed") or 0) <= 0:
            return [
                {
                    "id": "empty_book",
                    "text": "价格账没有完成的机会，这一层还看不出钱有没有买到该买的。",
                }
            ]
        return []

    @staticmethod
    def _fill(
        fill: Mapping[str, Any], quality: Mapping[str, Any]
    ) -> List[Dict[str, Any]]:
        del quality
        book = int(fill.get("price_completed") or 0)
        taken = int(fill.get("taken_count") or 0)
        leftover = int(fill.get("leftover_count") or 0)
        if book <= 0:
            return []
        if taken <= 0:
            return [
                {
                    "id": "no_buys",
                    "text": f"价格账 {book} 笔，账户一笔没买。",
                }
            ]
        if leftover <= 0:
            return [
                {
                    "id": "all_taken",
                    "text": f"价格账 {book} 笔账户都买到了。",
                }
            ]
        ratio = float(fill.get("fill_ratio") or 0.0)
        return [
            {
                "id": "fill_gap",
                "text": (
                    f"价格账 {book} 笔，买到 {taken}，漏掉 {leftover}"
                    f"（成交 {ratio:.1%}）。"
                ),
            }
        ]

    @staticmethod
    def _quality(
        quality: Mapping[str, Any], fill: Mapping[str, Any]
    ) -> List[Dict[str, Any]]:
        if int(fill.get("leftover_count") or 0) <= 0:
            return []
        taken = dict(quality.get("taken") or {})
        leftover = dict(quality.get("leftover") or {})
        gap = _as_float(quality.get("roi_gap"))
        taken_avg = _as_float(taken.get("avg_roi"))
        leftover_avg = _as_float(leftover.get("avg_roi"))
        if gap is None or taken_avg is None or leftover_avg is None:
            return []
        if gap >= _ROI_BIAS:
            return [
                {
                    "id": "leftover_better",
                    "text": (
                        f"漏掉的更好：均收益 {_pct_roi(leftover_avg)}，"
                        f"买到的 {_pct_roi(taken_avg)}。"
                        "资金 / 槽位 / 同股已持仓把好机会挤掉了。"
                    ),
                }
            ]
        if gap <= -_ROI_BIAS:
            return [
                {
                    "id": "leftover_worse",
                    "text": (
                        f"漏掉的更差：均收益 {_pct_roi(leftover_avg)}，"
                        f"买到的 {_pct_roi(taken_avg)}。"
                        "约束碰巧在过滤，不先当槽位不够。"
                    ),
                }
            ]
        return [
            {
                "id": "leftover_similar",
                "text": (
                    f"漏掉和买到的均收益差不多"
                    f"（{_pct_roi(leftover_avg)} vs {_pct_roi(taken_avg)}）。"
                ),
            }
        ]

    @staticmethod
    def _slots(fill: Mapping[str, Any]) -> List[Dict[str, Any]]:
        if not fill.get("slots_at_cap"):
            return []
        peak = int(fill.get("peak_open_positions") or 0)
        slots = int(fill.get("max_portfolio_size") or 0)
        leftover = int(fill.get("leftover_count") or 0)
        extra = f"满槽时还漏了 {leftover} 笔。" if leftover > 0 else ""
        return [
            {
                "id": "slots_at_cap",
                "text": f"槽位顶满：峰值 {peak}/{slots}。{extra}".rstrip(),
            }
        ]

    @staticmethod
    def _cash(fill: Mapping[str, Any]) -> List[Dict[str, Any]]:
        leftover = int(fill.get("leftover_count") or 0)
        util = float(fill.get("capital_utilization_ratio_pct") or 0.0)
        if leftover <= 0 or util >= _LOW_UTIL_PCT:
            return []
        peak = float(fill.get("peak_capital_utilization_ratio_pct") or 0.0)
        return [
            {
                "id": "cash_idle",
                "text": (
                    f"平时钱闲着：利用率均 {util:.1f}%，峰 {peak:.1f}%。"
                    "机会扎堆的日子才用上。"
                ),
            }
        ]

    @staticmethod
    def _groups(groups: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
        mismatch = _grouping_mismatch(groups)
        if mismatch is None:
            return []
        best, funded = mismatch
        return [
            {
                "id": "grouping_mismatch",
                "text": (
                    f"等权更赚的是{best}，账户主要买的是{funded}。"
                    "钱没有流向边更好的那一组。"
                ),
            }
        ]

    @staticmethod
    def _concentration(fill: Mapping[str, Any]) -> List[Dict[str, Any]]:
        n = int(fill.get("taken_count") or fill.get("completed_investments") or 0)
        if n < _MIN_CONCENTRATION_N:
            return []
        share = _as_share(fill.get("top5_profit_concentration_pct"))
        if share < _TOP5_CONCENTRATED_PCT / 100.0:
            return []
        return [
            {
                "id": "profit_concentrated",
                "text": f"账户利润靠头部：前 5 只占正收益 {share:.1%}。",
            }
        ]

    @staticmethod
    def _drawdown(
        drawdown: Mapping[str, Any], fill: Mapping[str, Any]
    ) -> List[Dict[str, Any]]:
        open_in_dd = drawdown.get("peak_open_in_drawdown")
        if open_in_dd is None:
            return []
        peak = int(open_in_dd)
        slots = int(fill.get("max_portfolio_size") or 0)
        if peak <= 1:
            return []
        if slots > 0 and peak < max(2, slots - 1):
            return []
        return [
            {
                "id": "drawdown_crowded",
                "text": f"回撤段同时持仓 {peak}，槽位里的票一起跌。",
            }
        ]


def _grouping_mismatch(
    groups: Sequence[Mapping[str, Any]],
) -> Optional[tuple]:
    by_kind: Dict[str, List[Mapping[str, Any]]] = {}
    for item in groups:
        kind = str(item.get("kind") or "").strip()
        if kind:
            by_kind.setdefault(kind, []).append(item)
    for kind in ("rsi", "exit", "year"):
        rows = [
            item
            for item in by_kind.get(kind, [])
            if int(item.get("price_count") or 0) >= _GROUP_MIN_N
        ]
        if len(rows) < 2:
            continue
        best = max(rows, key=lambda item: float(item.get("price_avg_roi") or 0.0))
        funded = max(rows, key=lambda item: int(item.get("taken_count") or 0))
        if str(best.get("name")) == str(funded.get("name")):
            continue
        if int(funded.get("taken_count") or 0) <= 0:
            continue
        return str(best.get("name") or ""), str(funded.get("name") or "")
    return None


def _pct_roi(value: float) -> str:
    return f"{value * 100.0:.1f}%"


def _as_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_share(value: Any) -> float:
    try:
        number = float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0
    if number > 1.0:
        return number / 100.0
    return number
