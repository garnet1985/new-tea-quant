"""枚举机会汇总衍生指标：档位分布、间隔/持续、涨跌停可交易性。

边界:
- 负责: 从 InvestmentRow / 每股机会数推导报告结论字段
- 不负责: 扫描 CSV、写 overall_report.json
- 调用方: OverallReport.build / present
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence

from core.modules.strategy.core.engines.shared.services.simulation_output import (
    InvestmentRow,
)
from core.utils.date.date_utils import DateUtils


@dataclass
class OpportunityCountBuckets:
    """每股机会数动态分档。"""

    min_count: int = 0
    max_count: int = 0
    bucket_count: int = 0
    labels: List[str] = field(default_factory=list)
    stock_counts: List[int] = field(default_factory=list)
    stock_ratios: List[float] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "opportunity_count_min": self.min_count,
            "opportunity_count_max": self.max_count,
            "opportunity_count_bucket_count": self.bucket_count,
            "opportunity_count_labels": list(self.labels),
            "opportunity_count_stock_counts": list(self.stock_counts),
            "opportunity_count_stock_ratios": list(self.stock_ratios),
        }

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "OpportunityCountBuckets":
        data = raw or {}
        return cls(
            min_count=int(data.get("opportunity_count_min") or 0),
            max_count=int(data.get("opportunity_count_max") or 0),
            bucket_count=int(data.get("opportunity_count_bucket_count") or 0),
            labels=[str(x) for x in (data.get("opportunity_count_labels") or [])],
            stock_counts=[
                int(v or 0) for v in (data.get("opportunity_count_stock_counts") or [])
            ],
            stock_ratios=[
                float(v or 0.0) for v in (data.get("opportunity_count_stock_ratios") or [])
            ],
        )


@dataclass
class TimingDispersion:
    """机会间隔 / 持续 / 分散度。"""

    mean_gap: float = 0.0
    mean_duration: float = 0.0
    std_gap: float = 0.0
    cv: float = 0.0
    dispersion_conclusion: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mean_gap": self.mean_gap,
            "mean_duration": self.mean_duration,
            "std_gap": self.std_gap,
            "cv": self.cv,
            "dispersion_conclusion": self.dispersion_conclusion,
        }

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "TimingDispersion":
        data = raw or {}
        return cls(
            mean_gap=float(data.get("mean_gap") or 0.0),
            mean_duration=float(data.get("mean_duration") or 0.0),
            std_gap=float(data.get("std_gap") or 0.0),
            cv=float(data.get("cv") or 0.0),
            dispersion_conclusion=str(data.get("dispersion_conclusion") or ""),
        )


@dataclass
class TradabilityMetrics:
    """涨跌停无法成交统计。"""

    buy_at_limit_up_count: int = 0
    buy_tradability_sample_count: int = 0
    limit_up_buy_ratio: float = 0.0
    sell_at_limit_down_count: int = 0
    sell_tradability_sample_count: int = 0
    limit_down_sell_ratio: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "buy_at_limit_up_count": self.buy_at_limit_up_count,
            "buy_tradability_sample_count": self.buy_tradability_sample_count,
            "limit_up_buy_ratio": self.limit_up_buy_ratio,
            "sell_at_limit_down_count": self.sell_at_limit_down_count,
            "sell_tradability_sample_count": self.sell_tradability_sample_count,
            "limit_down_sell_ratio": self.limit_down_sell_ratio,
        }

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "TradabilityMetrics":
        data = raw or {}
        return cls(
            buy_at_limit_up_count=int(data.get("buy_at_limit_up_count") or 0),
            buy_tradability_sample_count=int(
                data.get("buy_tradability_sample_count") or 0
            ),
            limit_up_buy_ratio=float(data.get("limit_up_buy_ratio") or 0.0),
            sell_at_limit_down_count=int(data.get("sell_at_limit_down_count") or 0),
            sell_tradability_sample_count=int(
                data.get("sell_tradability_sample_count") or 0
            ),
            limit_down_sell_ratio=float(data.get("limit_down_sell_ratio") or 0.0),
        )


def _safe_div(numer: float, denom: float) -> float:
    return (numer / denom) if denom else 0.0


def build_opportunity_count_buckets(
    counts: Sequence[int],
    *,
    total_stocks: int,
    target_bucket_count: int = 5,
) -> OpportunityCountBuckets:
    """按机会数动态分档（与 legacy EnumeratorReport 同算法）。"""
    if total_stocks <= 0:
        return OpportunityCountBuckets()
    values = [int(c) for c in counts]
    if not values:
        return OpportunityCountBuckets(
            min_count=0,
            max_count=0,
            bucket_count=1,
            labels=["0"],
            stock_counts=[total_stocks],
            stock_ratios=[100.0],
        )

    min_count = int(min(values))
    max_count = int(max(values))
    if min_count == max_count:
        return OpportunityCountBuckets(
            min_count=min_count,
            max_count=max_count,
            bucket_count=1,
            labels=[f"{min_count}"],
            stock_counts=[total_stocks],
            stock_ratios=[100.0],
        )

    span = max_count - min_count
    target_bucket_count = max(1, int(target_bucket_count))
    step = max(1, int(round(span / target_bucket_count)))

    edges: List[int] = [min_count]
    cursor = min_count
    while cursor < max_count:
        cursor = min(max_count, cursor + step)
        edges.append(cursor)
    bucket_count = max(1, len(edges) - 1)

    labels: List[str] = []
    bucket_values: List[int] = []
    for i in range(bucket_count):
        start = edges[i]
        end = edges[i + 1]
        if i < bucket_count - 1:
            end = max(start, end - 1)
        labels.append(f"{start}" if start == end else f"{start}-{end}")
        bucket_values.append(0)

    for c in values:
        for i in range(bucket_count):
            start = edges[i]
            end = (
                edges[i + 1]
                if i == bucket_count - 1
                else max(edges[i], edges[i + 1] - 1)
            )
            if start <= c <= end:
                bucket_values[i] += 1
                break

    ratios = [
        round(_safe_div(float(v), float(total_stocks)) * 100.0, 2)
        for v in bucket_values
    ]
    return OpportunityCountBuckets(
        min_count=min_count,
        max_count=max_count,
        bucket_count=bucket_count,
        labels=labels,
        stock_counts=bucket_values,
        stock_ratios=ratios,
    )


def _dispersion_conclusion(cv: float) -> str:
    if cv < 0.45:
        return "均匀"
    if cv < 0.8:
        return "中等聚集"
    return "较集中"


def compute_timing_dispersion(
    investments_by_entity: Dict[str, Sequence[InvestmentRow]],
) -> TimingDispersion:
    """相邻触发间隔 + 触发→结束持续 + 分散度（须按 entity 分组）。"""
    gaps: List[float] = []
    durations: List[float] = []
    for rows in investments_by_entity.values():
        rows_sorted = sorted(rows, key=lambda r: str(r.trigger_date or ""))
        trigger_dates = [
            DateUtils.normalize_str(str(r.trigger_date or ""))
            for r in rows_sorted
        ]
        trigger_dates = [d for d in trigger_dates if isinstance(d, str) and d]
        for idx in range(1, len(trigger_dates)):
            gaps.append(
                float(DateUtils.diff_days(trigger_dates[idx - 1], trigger_dates[idx]))
            )
        for r in rows_sorted:
            d0 = DateUtils.normalize_str(str(r.trigger_date or ""))
            d1 = DateUtils.normalize_str(str(r.exit_date or ""))
            if d0 and d1:
                durations.append(float(DateUtils.diff_days(d0, d1)))
            elif int(r.holding_days or 0) > 0:
                durations.append(float(r.holding_days))

    mean_gap = round(_safe_div(sum(gaps), len(gaps)), 2) if gaps else 0.0
    mean_duration = (
        round(_safe_div(sum(durations), len(durations)), 2) if durations else 0.0
    )
    if gaps:
        mean = sum(gaps) / len(gaps)
        variance = sum((x - mean) ** 2 for x in gaps) / len(gaps)
        std_gap = round(variance ** 0.5, 2)
    else:
        std_gap = 0.0
    cv = round(_safe_div(std_gap, mean_gap), 2) if mean_gap > 0 else 0.0
    return TimingDispersion(
        mean_gap=mean_gap,
        mean_duration=mean_duration,
        std_gap=std_gap,
        cv=cv,
        dispersion_conclusion=_dispersion_conclusion(cv),
    )


def compute_tradability(investments: Sequence[InvestmentRow]) -> TradabilityMetrics:
    """enter_at_limit / exit_at_limit → 涨停买不到 / 跌停卖不出。"""
    buy_sample = 0
    buy_limit = 0
    sell_sample = 0
    sell_limit = 0
    for row in investments:
        if row.enter_at_limit is not None:
            buy_sample += 1
            if bool(row.enter_at_limit):
                buy_limit += 1
        if row.exit_at_limit is not None:
            sell_sample += 1
            if bool(row.exit_at_limit):
                sell_limit += 1
    return TradabilityMetrics(
        buy_at_limit_up_count=buy_limit,
        buy_tradability_sample_count=buy_sample,
        limit_up_buy_ratio=round(_safe_div(float(buy_limit), float(buy_sample)) * 100.0, 1),
        sell_at_limit_down_count=sell_limit,
        sell_tradability_sample_count=sell_sample,
        limit_down_sell_ratio=round(
            _safe_div(float(sell_limit), float(sell_sample)) * 100.0, 1
        ),
    )


__all__ = [
    "OpportunityCountBuckets",
    "TimingDispersion",
    "TradabilityMetrics",
    "build_opportunity_count_buckets",
    "compute_timing_dispersion",
    "compute_tradability",
]
