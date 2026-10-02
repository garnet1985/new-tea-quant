"""把价格账事实收成基本结论。不编反事实百分比，不讲门贡献。"""
from __future__ import annotations

from typing import Any, List, Mapping, Optional, Sequence

_TOP5_CONCENTRATED = 0.50
_MIN_CONCENTRATION_N = 8
_YEAR_MIN_N = 3
_ROI_BIAS = 0.02
_WEAK_WIN = 0.45


class PriceConclude:
    """规则结论；一条 id 对应建议里的一条。"""

    @classmethod
    def run(cls, facts: Mapping[str, Any]) -> List[Dict[str, Any]]:
        book = dict(facts.get("book") or {})
        concentration = dict(facts.get("concentration") or {})
        exits = dict(facts.get("exits") or {})
        yearly = list(facts.get("yearly") or [])
        denoising = dict(facts.get("denoising") or {})
        out: List[Dict[str, Any]] = []
        out.extend(cls._edge(book))
        out.extend(cls._concentration(book, concentration))
        out.extend(cls._exits(exits))
        out.extend(cls._yearly(yearly))
        out.extend(cls._denoising(denoising))
        out.append(
            {
                "id": "not_account_return",
                "text": "这是等权机会账的边，不是组合层账户收益。",
            }
        )
        return out

    @staticmethod
    def _edge(book: Mapping[str, Any]) -> List[Dict[str, Any]]:
        n = int(book.get("completed_count") or 0)
        if n <= 0:
            return [
                {
                    "id": "empty_book",
                    "text": "去噪后没有完成的价格账，这一层还看不出策略赚不赚钱。",
                }
            ]
        avg_roi = float(book.get("avg_roi") or 0.0)
        win_rate = float(book.get("win_rate") or 0.0)
        factor = book.get("profit_factor")
        factor_n = float(factor) if factor is not None else None
        extra = f"盈亏比 {factor_n:.2f}。" if factor_n is not None else ""
        if avg_roi > 0 and (factor_n is None or factor_n >= 1.0):
            return [
                {
                    "id": "has_edge",
                    "text": (
                        f"去噪账有边：均收益 {_pct_roi(avg_roi)}，"
                        f"胜率 {win_rate:.1%}。{extra}"
                    ).rstrip(),
                }
            ]
        weak = "胜率也偏弱。" if win_rate < _WEAK_WIN else ""
        return [
            {
                "id": "no_edge",
                "text": (
                    f"去噪账没有边：均收益 {_pct_roi(avg_roi)}，"
                    f"胜率 {win_rate:.1%}。{weak}{extra}"
                ).rstrip(),
            }
        ]

    @staticmethod
    def _concentration(
        book: Mapping[str, Any],
        concentration: Mapping[str, Any],
    ) -> List[Dict[str, Any]]:
        n = int(concentration.get("sample_count") or book.get("completed_count") or 0)
        if n < _MIN_CONCENTRATION_N:
            return []
        share = float(concentration.get("top5_trades_profit_share") or 0.0)
        out: List[Dict[str, Any]] = []
        if share >= _TOP5_CONCENTRATED:
            out.append(
                {
                    "id": "profit_concentrated",
                    "text": f"利润靠头部：前 5 笔占正收益 {share:.1%}。",
                }
            )
        avg = float(book.get("avg_roi") or 0.0)
        without = concentration.get("avg_roi_without_top5_trades")
        if avg > 0 and without is not None and float(without) <= 0:
            out.append(
                {
                    "id": "profit_fragile",
                    "text": (
                        f"去掉赚得最多的 5 笔后均收益 {_pct_roi(float(without))}，"
                        "边不结实。"
                    ),
                }
            )
        return out

    @staticmethod
    def _exits(exits: Mapping[str, Any]) -> List[Dict[str, Any]]:
        mix = list(exits.get("by_reason") or [])
        if len(mix) < 2:
            return []
        worst = min(mix, key=lambda item: float(item.get("profit_sum") or 0.0))
        best = max(mix, key=lambda item: float(item.get("profit_sum") or 0.0))
        if float(worst.get("profit_sum") or 0.0) >= 0:
            return []
        return [
            {
                "id": "exit_mix",
                "text": (
                    f"利润主要从{best.get('label') or best.get('reason')}来"
                    f"（占净收益 {float(best.get('profit_share') or 0.0):.1%}）；"
                    f"{worst.get('label') or worst.get('reason')}拖后腿。"
                ),
            }
        ]

    @staticmethod
    def _yearly(yearly: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
        usable = [
            dict(item)
            for item in yearly
            if int(item.get("count") or 0) >= _YEAR_MIN_N
        ]
        if len(usable) < 2:
            return []
        signs = [
            1 if float(item.get("avg_roi") or 0.0) > 0 else -1 for item in usable
        ]
        if not (min(signs) < 0 < max(signs)):
            return []
        parts = [
            f"{item.get('year')} {_pct_roi(float(item.get('avg_roi') or 0.0))}"
            for item in usable
        ]
        return [
            {
                "id": "yearly_unstable",
                "text": "边随年份变号：" + "，".join(parts) + "。跨窗口请用 sw。",
            }
        ]

    @staticmethod
    def _denoising(denoising: Mapping[str, Any]) -> List[Dict[str, Any]]:
        if not denoising.get("enum_available"):
            return [
                {
                    "id": "no_enum_contrast",
                    "text": "没有枚举产物，合并掉的续命中好不好答不了。无差不能默认。",
                }
            ]
        merged = int(denoising.get("merged_count") or 0)
        skipped = (
            int(denoising.get("skipped_buy_at_limit_up") or 0)
            + int(denoising.get("skipped_sell_at_limit_down") or 0)
            + int(denoising.get("skipped_stock_status") or 0)
            + int(denoising.get("skipped_other") or 0)
        )
        if merged <= 0 and skipped <= 0:
            enum_count = denoising.get("enum_count")
            book_n = int(denoising.get("price_book_count") or 0)
            extra = (
                f"枚举 {enum_count} 笔，价格账 {book_n} 笔。"
                if enum_count is not None
                else ""
            )
            return [
                {
                    "id": "denoising_neutral",
                    "text": f"相对枚举没有并掉或涨跌停跳过。{extra}".rstrip(),
                }
            ]
        out: List[Dict[str, Any]] = []
        out.extend(_merged_bias(denoising, merged))
        limit_up = int(denoising.get("skipped_buy_at_limit_up") or 0)
        if limit_up > 0:
            out.append(
                {
                    "id": "tradability_skip",
                    "text": (
                        f"涨停买不进 {limit_up} 笔。"
                        "没进价格账是可交易性，不是锁仓。"
                    ),
                }
            )
        return out


def _merged_bias(denoising: Mapping[str, Any], merged: int) -> List[Dict[str, Any]]:
    if merged <= 0:
        return []
    text = f"并掉 {merged} 笔续命中。"
    book_mean = _as_float(denoising.get("book_mean_roi"))
    merged_mean = _as_float(denoising.get("merged_mean_roi"))
    if book_mean is None or merged_mean is None:
        return [{"id": "denoising_neutral", "text": text}]
    gap = merged_mean - book_mean
    if gap <= -_ROI_BIAS:
        text += (
            f"被并掉的均收益 {_pct_roi(merged_mean)}，"
            f"差于账本 {_pct_roi(book_mean)}。"
        )
        return [{"id": "merged_worse", "text": text}]
    if gap >= _ROI_BIAS:
        text += (
            f"被并掉的均收益 {_pct_roi(merged_mean)}，"
            f"好于账本 {_pct_roi(book_mean)}，去噪可能把边看矮了。"
        )
        return [{"id": "merged_better", "text": text}]
    text += "和账本均收益差不多。"
    return [{"id": "denoising_neutral", "text": text}]


def _pct_roi(value: float) -> str:
    return f"{value * 100.0:.1f}%"


def _as_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
