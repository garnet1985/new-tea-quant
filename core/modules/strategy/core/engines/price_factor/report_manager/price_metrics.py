"""价格回测衍生指标（ROI 分布 / 跳过归类）。

边界: 纯计算；无 IO。调用方: OverallReport / EntityListReport build。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict, List, Sequence

from core.modules.strategy.core.engines.price_factor.report_manager.investments import (
    PriceInvestmentRow,
)


@dataclass
class SkipCounters:
    """成交跳过计数（对齐 UI executionSkips）。"""

    skipped_buy_at_limit_up: int = 0
    skipped_sell_at_limit_down: int = 0
    skipped_stock_status: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skipped_buy_at_limit_up": self.skipped_buy_at_limit_up,
            "skipped_sell_at_limit_down": self.skipped_sell_at_limit_down,
            "skipped_stock_status": self.skipped_stock_status,
        }

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "SkipCounters":
        data = raw or {}
        return cls(
            skipped_buy_at_limit_up=int(data.get("skipped_buy_at_limit_up") or 0),
            skipped_sell_at_limit_down=int(data.get("skipped_sell_at_limit_down") or 0),
            skipped_stock_status=int(data.get("skipped_stock_status") or 0),
        )

    @classmethod
    def classify_reason(cls, reason: str) -> str:
        r = str(reason or "").strip().lower()
        if not r:
            return ""
        if "limit_up" in r or r in {"buy_at_limit_up", "enter_at_limit_up"}:
            return "buy_at_limit_up"
        if "limit_down" in r or r in {"sell_at_limit_down", "exit_at_limit_down"}:
            return "sell_at_limit_down"
        if "status" in r or "suspend" in r or "halt" in r:
            return "stock_status"
        return ""

    @classmethod
    def compute(cls, investments: Sequence[PriceInvestmentRow]) -> "SkipCounters":
        buy = 0
        sell = 0
        status = 0
        for row in investments:
            kind = cls.classify_reason(row.skip_reason)
            if kind == "buy_at_limit_up":
                buy += 1
            elif kind == "sell_at_limit_down":
                sell += 1
            elif kind == "stock_status":
                status += 1
        return cls(
            skipped_buy_at_limit_up=buy,
            skipped_sell_at_limit_down=sell,
            skipped_stock_status=status,
        )


@dataclass
class RoiDistribution:
    """ROI 分位 / 分桶（对齐 UI ROI 图；仅 goal 退出样本）。"""

    FORCED_EXIT_REASONS: ClassVar[frozenset] = frozenset(
        {
            "enumeration_end",
            "backtest_end",
            "simulate_end",
            "max_holding",
        }
    )
    NEG_BUCKET_LABELS: ClassVar[tuple] = (
        "[-100%, -50%)",
        "[-50%, -30%)",
        "[-30%, -20%)",
        "[-20%, -10%)",
        "[-10%, -5%)",
        "[-5%, 0%)",
    )
    POS_BUCKET_LABELS: ClassVar[tuple] = (
        "[0%, 5%)",
        "[5%, 10%)",
        "[10%, 20%)",
        "[20%, 30%)",
        "[30%, 50%)",
        "[50%, 100%)",
        ">100%",
    )

    roi_percentile_labels: List[str] = field(default_factory=list)
    roi_percentile_values: List[float] = field(default_factory=list)
    roi_p10: float = 0.0
    roi_p20: float = 0.0
    roi_p30: float = 0.0
    roi_p40: float = 0.0
    roi_p50: float = 0.0
    roi_p60: float = 0.0
    roi_p70: float = 0.0
    roi_p80: float = 0.0
    roi_p90: float = 0.0
    roi_p25: float = 0.0
    roi_p75: float = 0.0
    roi_iqr: float = 0.0
    roi_std_pct: float = 0.0
    roi_conclusion: str = ""
    roi_bucket_labels: List[str] = field(default_factory=list)
    roi_bucket_counts: List[int] = field(default_factory=list)
    roi_bucket_bin_count: int = 0
    roi_truncated_exit_count: int = 0
    roi_distribution_sample_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "roi_percentile_labels": list(self.roi_percentile_labels),
            "roi_percentile_values": list(self.roi_percentile_values),
            "roi_p10": self.roi_p10,
            "roi_p20": self.roi_p20,
            "roi_p30": self.roi_p30,
            "roi_p40": self.roi_p40,
            "roi_p50": self.roi_p50,
            "roi_p60": self.roi_p60,
            "roi_p70": self.roi_p70,
            "roi_p80": self.roi_p80,
            "roi_p90": self.roi_p90,
            "roi_p25": self.roi_p25,
            "roi_p75": self.roi_p75,
            "roi_iqr": self.roi_iqr,
            "roi_std_pct": self.roi_std_pct,
            "roi_conclusion": self.roi_conclusion,
            "roi_bucket_labels": list(self.roi_bucket_labels),
            "roi_bucket_counts": list(self.roi_bucket_counts),
            "roi_bucket_bin_count": self.roi_bucket_bin_count,
            "roi_truncated_exit_count": self.roi_truncated_exit_count,
            "roi_distribution_sample_count": self.roi_distribution_sample_count,
        }

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "RoiDistribution":
        data = raw or {}
        return cls(
            roi_percentile_labels=[str(x) for x in (data.get("roi_percentile_labels") or [])],
            roi_percentile_values=[
                float(v or 0.0) for v in (data.get("roi_percentile_values") or [])
            ],
            roi_p10=float(data.get("roi_p10") or 0.0),
            roi_p20=float(data.get("roi_p20") or 0.0),
            roi_p30=float(data.get("roi_p30") or 0.0),
            roi_p40=float(data.get("roi_p40") or 0.0),
            roi_p50=float(data.get("roi_p50") or 0.0),
            roi_p60=float(data.get("roi_p60") or 0.0),
            roi_p70=float(data.get("roi_p70") or 0.0),
            roi_p80=float(data.get("roi_p80") or 0.0),
            roi_p90=float(data.get("roi_p90") or 0.0),
            roi_p25=float(data.get("roi_p25") or 0.0),
            roi_p75=float(data.get("roi_p75") or 0.0),
            roi_iqr=float(data.get("roi_iqr") or 0.0),
            roi_std_pct=float(data.get("roi_std_pct") or 0.0),
            roi_conclusion=str(data.get("roi_conclusion") or ""),
            roi_bucket_labels=[str(x) for x in (data.get("roi_bucket_labels") or [])],
            roi_bucket_counts=[
                int(v or 0) for v in (data.get("roi_bucket_counts") or [])
            ],
            roi_bucket_bin_count=int(data.get("roi_bucket_bin_count") or 0),
            roi_truncated_exit_count=int(data.get("roi_truncated_exit_count") or 0),
            roi_distribution_sample_count=int(
                data.get("roi_distribution_sample_count") or 0
            ),
        )

    @classmethod
    def is_forced_exit(cls, row: PriceInvestmentRow) -> bool:
        reason = str(row.exit_reason or "").strip().lower()
        return reason in cls.FORCED_EXIT_REASONS

    @classmethod
    def is_expired(cls, row: PriceInvestmentRow) -> bool:
        reason = str(row.exit_reason or "").strip().lower()
        return "expir" in reason or reason == "expired"

    @classmethod
    def roi_as_percent(cls, roi: float) -> float:
        r = float(roi)
        if not math.isfinite(r) or r == 0.0:
            return 0.0 if r == 0.0 else float("nan")
        if abs(r) < 1.0:
            return r * 100.0
        return r

    @classmethod
    def _percentile_linear(cls, sorted_vals: List[float], p: float) -> float:
        n = len(sorted_vals)
        if n == 0:
            return float("nan")
        if n == 1:
            return sorted_vals[0]
        k = (n - 1) * (p / 100.0)
        f = math.floor(k)
        c = min(math.ceil(k), n - 1)
        if f >= c:
            return sorted_vals[c]
        return sorted_vals[f] * (c - k) + sorted_vals[c] * (k - f)

    @classmethod
    def _sample_std(cls, vals: List[float]) -> float:
        n = len(vals)
        if n < 2:
            return 0.0
        mean = sum(vals) / n
        var = sum((x - mean) ** 2 for x in vals) / (n - 1)
        if not math.isfinite(var) or var < 0:
            return 0.0
        return round(math.sqrt(var), 2)

    @classmethod
    def _neg_bucket_index(cls, x: float) -> int:
        if x < -50.0:
            return 0
        if x < -30.0:
            return 1
        if x < -20.0:
            return 2
        if x < -10.0:
            return 3
        if x < -5.0:
            return 4
        return 5

    @classmethod
    def _pos_bucket_index(cls, x: float) -> int:
        if x >= 100.0:
            return 6
        if x >= 50.0:
            return 5
        if x >= 30.0:
            return 4
        if x >= 20.0:
            return 3
        if x >= 10.0:
            return 2
        if x >= 5.0:
            return 1
        return 0

    @classmethod
    def _conclusion(cls, p50: float, iqr: float) -> str:
        if not math.isfinite(p50):
            return ""
        if p50 >= 5.0 and iqr < 20.0:
            return "偏正且集中"
        if p50 >= 0.0:
            return "中位偏正"
        if p50 < 0.0 and iqr < 20.0:
            return "偏负且集中"
        return "分散"

    @classmethod
    def compute(cls, investments: Sequence[PriceInvestmentRow]) -> "RoiDistribution":
        rois: List[float] = []
        truncated = 0
        for row in investments:
            if row.skip_reason:
                continue
            lifecycle = str(row.lifecycle or "").strip().lower()
            if lifecycle in {"open", "holding", "active"} and not row.exit_date:
                continue
            if cls.is_forced_exit(row):
                truncated += 1
                continue
            if not row.exit_date and lifecycle != "complete":
                continue
            pct = cls.roi_as_percent(float(row.roi or 0.0))
            if math.isfinite(pct):
                rois.append(pct)

        empty = cls(
            roi_truncated_exit_count=truncated,
            roi_distribution_sample_count=len(rois),
        )
        if not rois:
            return empty

        xs = sorted(rois)
        points = [10, 20, 30, 40, 50, 60, 70, 80, 90]
        pv = [round(cls._percentile_linear(xs, p), 2) for p in points]
        if len(pv) != 9 or any(not math.isfinite(x) for x in pv):
            return empty

        p25 = round(cls._percentile_linear(xs, 25.0), 2)
        p75 = round(cls._percentile_linear(xs, 75.0), 2)
        iqr = round(p75 - p25, 2) if math.isfinite(p25) and math.isfinite(p75) else 0.0
        labels = list(cls.NEG_BUCKET_LABELS) + list(cls.POS_BUCKET_LABELS)
        counts = [0] * len(labels)
        neg_n = len(cls.NEG_BUCKET_LABELS)
        for raw in rois:
            x = float(raw)
            if x < 0:
                counts[cls._neg_bucket_index(x)] += 1
            else:
                counts[neg_n + cls._pos_bucket_index(x)] += 1

        return cls(
            roi_percentile_labels=[f"{p}%分位" for p in points],
            roi_percentile_values=pv,
            roi_p10=pv[0],
            roi_p20=pv[1],
            roi_p30=pv[2],
            roi_p40=pv[3],
            roi_p50=pv[4],
            roi_p60=pv[5],
            roi_p70=pv[6],
            roi_p80=pv[7],
            roi_p90=pv[8],
            roi_p25=p25,
            roi_p75=p75,
            roi_iqr=iqr,
            roi_std_pct=cls._sample_std(rois),
            roi_conclusion=cls._conclusion(pv[4], iqr),
            roi_bucket_labels=labels,
            roi_bucket_counts=counts,
            roi_bucket_bin_count=len(labels),
            roi_truncated_exit_count=truncated,
            roi_distribution_sample_count=len(rois),
        )


__all__ = ["SkipCounters", "RoiDistribution"]
