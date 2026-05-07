#!/usr/bin/env python3
"""机会枚举报告数据类。"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from core.infra.project_context import PathManager
from core.modules.strategy.engines.shared.report_base import ReportBase
from core.utils.date.date_utils import DateUtils


@dataclass
class EnumeratorReport(ReportBase):
    total_opportunities: int
    total_stocks: int
    trigger_stocks: int
    trigger_ratio: float
    avg_per_stock: float
    completed_ratio: float
    completed_count: int
    unfinished_count: int
    mean_gap: float
    mean_duration: float
    std_gap: float
    cv: float
    dispersion_conclusion: str
    percentile_labels: List[str]
    percentile_values: List[float]
    opportunity_count_min: int
    opportunity_count_max: int
    opportunity_count_bucket_count: int
    opportunity_count_labels: List[str]
    opportunity_count_stock_counts: List[int]
    opportunity_count_stock_ratios: List[float]
    stock_rows: List[Dict[str, Any]]

    @classmethod
    def collect(cls, source: Path, **kwargs: Any) -> List[Dict[str, Any]]:
        opportunities: List[Dict[str, Any]] = []
        for entry in source.iterdir():
            if not entry.is_file() or not entry.name.endswith("_opportunities.csv"):
                continue
            stock_id = entry.name[: -len("_opportunities.csv")]
            with entry.open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    payload = dict(row or {})
                    payload["stock_id"] = stock_id
                    opportunities.append(payload)
        return opportunities

    @classmethod
    def compute(
        cls,
        collected: List[Dict[str, Any]],
        **kwargs: Any,
    ) -> "EnumeratorReport":
        return cls.from_opportunities_with_total_stocks(
            opportunities=collected,
            total_stocks_hint=kwargs.get("total_stocks_hint"),
        )

    @staticmethod
    def _quantile(values: List[float], q: float) -> float:
        if not values:
            return 0.0
        if q <= 0:
            return float(values[0])
        if q >= 1:
            return float(values[-1])
        # nearest-rank percentile:
        # sorted values, rank = ceil(q * n), 1-indexed
        n = len(values)
        rank = int(q * n)
        if (q * n) > rank:
            rank += 1
        rank = min(max(rank, 1), n)
        return float(values[rank - 1])

    @staticmethod
    def _build_opportunity_count_buckets(
        counts: List[int],
        *,
        total_stocks: int,
        target_bucket_count: int = 5,
    ) -> tuple[int, int, int, List[str], List[int], List[float]]:
        if total_stocks <= 0:
            return 0, 0, 0, [], [], []
        if not counts:
            return 0, 0, 1, ["0"], [total_stocks], [100.0]

        min_count = int(min(counts))
        max_count = max(counts)
        if min_count == max_count:
            return min_count, max_count, 1, [f"{min_count}"], [total_stocks], [100.0]

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

        for c in counts:
            for i in range(bucket_count):
                start = edges[i]
                end = edges[i + 1] if i == bucket_count - 1 else max(edges[i], edges[i + 1] - 1)
                if start <= c <= end:
                    bucket_values[i] += 1
                    break

        ratios = [round(ReportBase.safe_div(v, total_stocks) * 100.0, 2) for v in bucket_values]
        return min_count, max_count, bucket_count, labels, bucket_values, ratios

    @classmethod
    def from_opportunities(cls, opportunities: List[Dict[str, Any]]) -> "EnumeratorReport":
        return cls.from_opportunities_with_total_stocks(
            opportunities=opportunities,
            total_stocks_hint=None,
        )

    @classmethod
    def from_opportunities_with_total_stocks(
        cls,
        *,
        opportunities: List[Dict[str, Any]],
        total_stocks_hint: int | None,
    ) -> "EnumeratorReport":
        by_stock: Dict[str, List[Dict[str, Any]]] = {}
        for row in opportunities:
            if not isinstance(row, dict):
                continue
            sid = str(row.get("stock_id") or "").strip()
            if not sid:
                continue
            by_stock.setdefault(sid, []).append(row)

        total_opportunities = len(opportunities)
        total_stocks = int(total_stocks_hint) if total_stocks_hint is not None else len(by_stock)
        trigger_stocks = len(by_stock)
        completed_count = 0
        unfinished_count = 0
        for row in opportunities:
            sell_reason = str((row or {}).get("sell_reason") or "").lower()
            if sell_reason in {"enumeration_end", "backtest_end"}:
                unfinished_count += 1
                continue
            status = str((row or {}).get("status") or "").lower()
            if status in {"open", "active", "testing"}:
                unfinished_count += 1
            else:
                completed_count += 1
        unfinished_count = max(unfinished_count, total_opportunities - completed_count)
        trigger_ratio = round(ReportBase.safe_div(trigger_stocks, total_stocks) * 100.0, 1)
        avg_per_stock = round(ReportBase.safe_div(total_opportunities, trigger_stocks), 2)
        completed_ratio = round(ReportBase.safe_div(completed_count, total_opportunities) * 100.0, 1)

        per_stock_counts = sorted(float(len(rows)) for rows in by_stock.values())
        per_stock_count_ints = [int(x) for x in per_stock_counts]
        percentile_labels = [
            "10%分位",
            "20%分位",
            "30%分位",
            "40%分位",
            "50%分位",
            "60%分位",
            "70%分位",
            "80%分位",
            "90%分位",
        ]
        percentile_values = [
            round(cls._quantile(per_stock_counts, q), 2)
            for q in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)
        ]
        all_stock_count_ints = list(per_stock_count_ints)
        zero_count_stocks = max(0, total_stocks - trigger_stocks)
        if zero_count_stocks > 0:
            all_stock_count_ints.extend([0] * zero_count_stocks)
        (
            opportunity_count_min,
            opportunity_count_max,
            opportunity_count_bucket_count,
            opportunity_count_labels,
            opportunity_count_stock_counts,
            opportunity_count_stock_ratios,
        ) = cls._build_opportunity_count_buckets(
            all_stock_count_ints,
            total_stocks=total_stocks,
            target_bucket_count=5,
        )

        gaps: List[float] = []
        durations: List[float] = []
        stock_rows: List[Dict[str, Any]] = []
        for sid, rows in by_stock.items():
            rows_sorted = sorted(rows, key=lambda r: str((r or {}).get("trigger_date") or ""))
            trigger_dates = [
                DateUtils.normalize_str(str((r or {}).get("trigger_date") or ""))
                for r in rows_sorted
            ]
            trigger_dates = [d for d in trigger_dates if isinstance(d, str) and d]
            stock_gaps: List[float] = []
            for idx in range(1, len(trigger_dates)):
                stock_gaps.append(float(DateUtils.diff_days(trigger_dates[idx - 1], trigger_dates[idx])))
            gaps.extend(stock_gaps)
            for r in rows_sorted:
                d0 = DateUtils.normalize_str(str((r or {}).get("trigger_date") or ""))
                d1 = DateUtils.normalize_str(str((r or {}).get("sell_date") or ""))
                if d0 and d1:
                    durations.append(float(DateUtils.diff_days(d0, d1)))
            completed_i = sum(
                1 for r in rows_sorted if str((r or {}).get("status") or "").lower() == "completed"
            )
            count_i = len(rows_sorted)
            row_completion = round(ReportBase.safe_div(completed_i, count_i) * 100.0, 1)
            avg_gap_i = round(ReportBase.safe_div(sum(stock_gaps), len(stock_gaps)), 1) if stock_gaps else 0.0
            stock_rows.append(
                {
                    "stock_id": sid,
                    "stock_name": sid,
                    "opportunities": count_i,
                    "completion_rate": row_completion,
                    "trigger_span_days": avg_gap_i,
                }
            )
        stock_rows.sort(key=lambda r: int(r.get("opportunities") or 0), reverse=True)
        stock_rows = stock_rows[:100]

        mean_gap = round(ReportBase.safe_div(sum(gaps), len(gaps)), 2) if gaps else 0.0
        mean_duration = round(ReportBase.safe_div(sum(durations), len(durations)), 2) if durations else 0.0
        if gaps:
            mean = sum(gaps) / len(gaps)
            variance = sum((x - mean) ** 2 for x in gaps) / len(gaps)
            std_gap = round(variance ** 0.5, 2)
        else:
            std_gap = 0.0
        cv = round(ReportBase.safe_div(std_gap, mean_gap), 2) if mean_gap > 0 else 0.0
        if cv < 0.45:
            dispersion = "机会出现较均匀，节奏相对稳定"
        elif cv < 0.8:
            dispersion = "机会有一定聚集，节奏波动中等"
        else:
            dispersion = "机会集中出现，节奏波动较大"

        return cls(
            total_opportunities=total_opportunities,
            total_stocks=total_stocks,
            trigger_stocks=trigger_stocks,
            trigger_ratio=trigger_ratio,
            avg_per_stock=avg_per_stock,
            completed_ratio=completed_ratio,
            completed_count=completed_count,
            unfinished_count=unfinished_count,
            mean_gap=mean_gap,
            mean_duration=mean_duration,
            std_gap=std_gap,
            cv=cv,
            dispersion_conclusion=dispersion,
            percentile_labels=percentile_labels,
            percentile_values=percentile_values,
            opportunity_count_min=opportunity_count_min,
            opportunity_count_max=opportunity_count_max,
            opportunity_count_bucket_count=opportunity_count_bucket_count,
            opportunity_count_labels=opportunity_count_labels,
            opportunity_count_stock_counts=opportunity_count_stock_counts,
            opportunity_count_stock_ratios=opportunity_count_stock_ratios,
            stock_rows=stock_rows,
        )

    @classmethod
    def from_output_dir(
        cls,
        output_dir: Path,
        *,
        total_stocks_hint: int | None = None,
    ) -> "EnumeratorReport":
        return cls.compute(
            cls.collect(output_dir),
            total_stocks_hint=total_stocks_hint,
        )

    @classmethod
    def from_per_stock_bundles(
        cls,
        bundles_by_stock: Dict[str, Dict[str, Any]],
        *,
        stock_universe: List[str],
    ) -> "EnumeratorReport":
        """由各 job 在内存中带回的摘要生成报告，避免跑完后再读每只股票的 CSV。

        每股 ``bundles_by_stock[sid]`` 须含：
        ``stock_name``, ``opportunity_count``, ``report_completed_count``, ``report_unfinished_count``,
        ``status_completed_count``, ``trigger_gap_days``（list[float]）,
        ``holding_duration_days``（list[float]）。
        缺股的 key 视为无机会。
        """
        total_stocks = len(stock_universe)
        if total_stocks <= 0:
            return cls.from_opportunities_with_total_stocks(opportunities=[], total_stocks_hint=0)

        def _bundle_for(sid: str) -> Dict[str, Any]:
            raw = bundles_by_stock.get(sid)
            return raw if isinstance(raw, dict) else {}

        total_opportunities = 0
        completed_count = 0
        unfinished_count = 0
        gaps: List[float] = []
        durations: List[float] = []
        trigger_stocks = 0

        for sid in stock_universe:
            b = _bundle_for(sid)
            n = int(b.get("opportunity_count") or 0)
            total_opportunities += n
            completed_count += int(b.get("report_completed_count") or 0)
            unfinished_count += int(b.get("report_unfinished_count") or 0)
            if n > 0:
                trigger_stocks += 1
            gaps.extend(float(x) for x in (b.get("trigger_gap_days") or []) if isinstance(x, (int, float)))
            durations.extend(float(x) for x in (b.get("holding_duration_days") or []) if isinstance(x, (int, float)))

        unfinished_count = max(unfinished_count, total_opportunities - completed_count)
        trigger_ratio = round(ReportBase.safe_div(trigger_stocks, total_stocks) * 100.0, 1)
        avg_per_stock = round(ReportBase.safe_div(total_opportunities, trigger_stocks), 2) if trigger_stocks else 0.0
        completed_ratio = round(ReportBase.safe_div(completed_count, total_opportunities) * 100.0, 1)

        per_stock_counts = sorted(
            float(_bundle_for(sid).get("opportunity_count") or 0)
            for sid in stock_universe
            if int(_bundle_for(sid).get("opportunity_count") or 0) > 0
        )
        percentile_labels = [
            "10%分位",
            "20%分位",
            "30%分位",
            "40%分位",
            "50%分位",
            "60%分位",
            "70%分位",
            "80%分位",
            "90%分位",
        ]
        percentile_values = [
            round(cls._quantile(per_stock_counts, q), 2)
            for q in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)
        ]
        all_stock_count_ints = [int(x) for x in per_stock_counts]
        zero_count_stocks = max(0, total_stocks - trigger_stocks)
        if zero_count_stocks > 0:
            all_stock_count_ints.extend([0] * zero_count_stocks)
        (
            opportunity_count_min,
            opportunity_count_max,
            opportunity_count_bucket_count,
            opportunity_count_labels,
            opportunity_count_stock_counts,
            opportunity_count_stock_ratios,
        ) = cls._build_opportunity_count_buckets(
            all_stock_count_ints,
            total_stocks=total_stocks,
            target_bucket_count=5,
        )

        stock_rows: List[Dict[str, Any]] = []
        for sid in stock_universe:
            b = _bundle_for(sid)
            count_i = int(b.get("opportunity_count") or 0)
            if count_i <= 0:
                continue
            completed_i = int(b.get("status_completed_count") or 0)
            row_completion = round(ReportBase.safe_div(completed_i, count_i) * 100.0, 1)
            tg = b.get("trigger_gap_days") or []
            gaps_i = [float(x) for x in tg if isinstance(x, (int, float))]
            avg_gap_i = round(ReportBase.safe_div(sum(gaps_i), len(gaps_i)), 1) if gaps_i else 0.0
            stock_rows.append(
                {
                    "stock_id": sid,
                    "stock_name": str(b.get("stock_name") or sid),
                    "opportunities": count_i,
                    "completion_rate": row_completion,
                    "trigger_span_days": avg_gap_i,
                }
            )
        stock_rows.sort(key=lambda r: int(r.get("opportunities") or 0), reverse=True)
        stock_rows = stock_rows[:100]

        mean_gap = round(ReportBase.safe_div(sum(gaps), len(gaps)), 2) if gaps else 0.0
        mean_duration = round(ReportBase.safe_div(sum(durations), len(durations)), 2) if durations else 0.0
        if gaps:
            mean = sum(gaps) / len(gaps)
            variance = sum((x - mean) ** 2 for x in gaps) / len(gaps)
            std_gap = round(variance ** 0.5, 2)
        else:
            std_gap = 0.0
        cv = round(ReportBase.safe_div(std_gap, mean_gap), 2) if mean_gap > 0 else 0.0
        if cv < 0.45:
            dispersion = "机会出现较均匀，节奏相对稳定"
        elif cv < 0.8:
            dispersion = "机会有一定聚集，节奏波动中等"
        else:
            dispersion = "机会集中出现，节奏波动较大"

        return cls(
            total_opportunities=total_opportunities,
            total_stocks=total_stocks,
            trigger_stocks=trigger_stocks,
            trigger_ratio=trigger_ratio,
            avg_per_stock=avg_per_stock,
            completed_ratio=completed_ratio,
            completed_count=completed_count,
            unfinished_count=unfinished_count,
            mean_gap=mean_gap,
            mean_duration=mean_duration,
            std_gap=std_gap,
            cv=cv,
            dispersion_conclusion=dispersion,
            percentile_labels=percentile_labels,
            percentile_values=percentile_values,
            opportunity_count_min=opportunity_count_min,
            opportunity_count_max=opportunity_count_max,
            opportunity_count_bucket_count=opportunity_count_bucket_count,
            opportunity_count_labels=opportunity_count_labels,
            opportunity_count_stock_counts=opportunity_count_stock_counts,
            opportunity_count_stock_ratios=opportunity_count_stock_ratios,
            stock_rows=stock_rows,
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EnumeratorReport":
        return cls(
            total_opportunities=int(data.get("total_opportunities", 0) or 0),
            total_stocks=int(data.get("total_stocks", 0) or 0),
            trigger_stocks=int(data.get("trigger_stocks", 0) or 0),
            trigger_ratio=float(data.get("trigger_ratio", 0.0) or 0.0),
            avg_per_stock=float(data.get("avg_per_stock", 0.0) or 0.0),
            completed_ratio=float(data.get("completed_ratio", 0.0) or 0.0),
            completed_count=int(data.get("completed_count", 0) or 0),
            unfinished_count=int(data.get("unfinished_count", 0) or 0),
            mean_gap=float(data.get("mean_gap", 0.0) or 0.0),
            mean_duration=float(data.get("mean_duration", 0.0) or 0.0),
            std_gap=float(data.get("std_gap", 0.0) or 0.0),
            cv=float(data.get("cv", 0.0) or 0.0),
            dispersion_conclusion=str(data.get("dispersion_conclusion", "") or ""),
            percentile_labels=list(data.get("percentile_labels", []) or []),
            percentile_values=[float(v or 0.0) for v in (data.get("percentile_values", []) or [])],
            opportunity_count_min=int(data.get("opportunity_count_min", 0) or 0),
            opportunity_count_max=int(data.get("opportunity_count_max", 0) or 0),
            opportunity_count_bucket_count=int(data.get("opportunity_count_bucket_count", 0) or 0),
            opportunity_count_labels=list(data.get("opportunity_count_labels", []) or []),
            opportunity_count_stock_counts=[
                int(v or 0) for v in (data.get("opportunity_count_stock_counts", []) or [])
            ],
            opportunity_count_stock_ratios=[
                float(v or 0.0) for v in (data.get("opportunity_count_stock_ratios", []) or [])
            ],
            stock_rows=list(data.get("stock_rows", []) or []),
        )

    def to_bff_payload(self, *, include_stock_rows: bool = False) -> Dict[str, Any]:
        """``include_stock_rows``：逐股明细另存 ``0_stock_ref.json`` 时不写入报告，避免与 ref 重复。"""
        out: Dict[str, Any] = {
            "enumMetrics": {
                "totalOpportunities": self.total_opportunities,
                "totalStocks": self.total_stocks,
                "triggerStocks": self.trigger_stocks,
                "triggerRatio": self.trigger_ratio,
                "avgPerStock": self.avg_per_stock,
                "completedRatio": self.completed_ratio,
                "completedCount": self.completed_count,
                "unfinishedCount": self.unfinished_count,
                "meanGap": self.mean_gap,
                "meanDuration": self.mean_duration,
                "stdGap": self.std_gap,
                "cv": self.cv,
                "dispersionConclusion": self.dispersion_conclusion,
                "percentileLabels": self.percentile_labels,
                "percentileValues": self.percentile_values,
                "opportunityCountMin": self.opportunity_count_min,
                "opportunityCountMax": self.opportunity_count_max,
                "opportunityCountBucketCount": self.opportunity_count_bucket_count,
                "opportunityCountLabels": self.opportunity_count_labels,
                "opportunityCountStockCounts": self.opportunity_count_stock_counts,
                "opportunityCountStockRatios": self.opportunity_count_stock_ratios,
            },
        }
        if include_stock_rows:
            out["stockRows"] = self.stock_rows
        return out

    @classmethod
    def from_bff_payload(cls, payload: Dict[str, Any]) -> "EnumeratorReport":
        metrics = payload.get("enumMetrics") if isinstance(payload, dict) else {}
        if not isinstance(metrics, dict):
            metrics = {}
        return cls(
            total_opportunities=int(metrics.get("totalOpportunities", 0) or 0),
            total_stocks=int(metrics.get("totalStocks", 0) or 0),
            trigger_stocks=int(metrics.get("triggerStocks", 0) or 0),
            trigger_ratio=float(metrics.get("triggerRatio", 0.0) or 0.0),
            avg_per_stock=float(metrics.get("avgPerStock", 0.0) or 0.0),
            completed_ratio=float(metrics.get("completedRatio", 0.0) or 0.0),
            completed_count=int(metrics.get("completedCount", 0) or 0),
            unfinished_count=int(metrics.get("unfinishedCount", 0) or 0),
            mean_gap=float(metrics.get("meanGap", 0.0) or 0.0),
            mean_duration=float(metrics.get("meanDuration", 0.0) or 0.0),
            std_gap=float(metrics.get("stdGap", 0.0) or 0.0),
            cv=float(metrics.get("cv", 0.0) or 0.0),
            dispersion_conclusion=str(metrics.get("dispersionConclusion", "") or ""),
            percentile_labels=list(metrics.get("percentileLabels", []) or []),
            percentile_values=[float(v or 0.0) for v in (metrics.get("percentileValues", []) or [])],
            opportunity_count_min=int(metrics.get("opportunityCountMin", 0) or 0),
            opportunity_count_max=int(metrics.get("opportunityCountMax", 0) or 0),
            opportunity_count_bucket_count=int(metrics.get("opportunityCountBucketCount", 0) or 0),
            opportunity_count_labels=list(metrics.get("opportunityCountLabels", []) or []),
            opportunity_count_stock_counts=[
                int(v or 0) for v in (metrics.get("opportunityCountStockCounts", []) or [])
            ],
            opportunity_count_stock_ratios=[
                float(v or 0.0) for v in (metrics.get("opportunityCountStockRatios", []) or [])
            ],
            stock_rows=list(payload.get("stockRows", []) or []) if isinstance(payload, dict) else [],
        )

    def to_console_lines(self) -> List[str]:
        lines = [
            f"📊 机会总数: {self.total_opportunities}",
            f"🏷️ 扫描股票数: {self.total_stocks}",
            f"🎯 至少出现过机会的股票数: {self.trigger_stocks}",
            f"📈 触发比例: {self.trigger_ratio}%",
            f"✅ 已完成机会数: {self.completed_count}",
            f"⏳ 未完成机会数: {self.unfinished_count}",
            f"📉 完成率: {self.completed_ratio}%",
            f"📐 平均每只股票机会数: {self.avg_per_stock}",
            f"⏱️ 平均两次触发间隔: {self.mean_gap} 天",
            f"⌛ 平均单笔持续: {self.mean_duration} 天",
            f"📏 触发间隔标准差: {self.std_gap} 天",
            f"📐 变异系数(CV): {self.cv}",
            f"💡 节奏结论: {self.dispersion_conclusion}",
        ]
        if self.percentile_labels and self.percentile_values:
            pct_pairs = zip(self.percentile_labels, self.percentile_values)
            pv = " · ".join(f"{lb} {val}" for lb, val in pct_pairs)
            lines.append(f"📊 每股机会数分位: {pv}")
        if self.opportunity_count_labels:
            lines.append(
                f"📦 机会数区间分布 [{self.opportunity_count_min}~{self.opportunity_count_max}] "
                f"（约 {max(1, self.opportunity_count_bucket_count)} 档）"
            )
            for idx, label in enumerate(self.opportunity_count_labels):
                count = (
                    self.opportunity_count_stock_counts[idx]
                    if idx < len(self.opportunity_count_stock_counts)
                    else 0
                )
                ratio = (
                    self.opportunity_count_stock_ratios[idx]
                    if idx < len(self.opportunity_count_stock_ratios)
                    else 0.0
                )
                lines.append(f"   ▸ {label} 次: {count} 只 ({ratio}%)")
        return lines

    def write_bff_payload(self, output_dir: Path, *, include_stock_rows: bool = False) -> None:
        with (output_dir / "0_report_enum.json").open("w", encoding="utf-8") as f:
            json.dump(
                self.to_bff_payload(include_stock_rows=include_stock_rows),
                f,
                indent=2,
                ensure_ascii=False,
            )

    @classmethod
    def load(
        cls,
        source: Path,
        **kwargs: Any,
    ) -> "EnumeratorReport":
        report_path = source / "0_report_enum.json"
        if not report_path.exists():
            return cls.from_bff_payload({})
        try:
            payload = json.loads(report_path.read_text(encoding="utf-8"))
            return cls.from_bff_payload(payload if isinstance(payload, dict) else {})
        except Exception:
            return cls.from_bff_payload({})

    def write(self, output_dir: Path, **kwargs: Any) -> None:
        self.write_bff_payload(output_dir)

    @classmethod
    def present(cls, **kwargs: Any) -> None:
        strategy_name = str(kwargs.get("strategy_name") or "")
        summary_results: List[Dict[str, Any]] = kwargs.get("summary_results") or []
        total_opps = (
            int(summary_results[0].get("opportunities", 0) or 0)
            if summary_results
            else 0
        )
        label = strategy_name.strip() or "策略"
        sep = "=" * 60
        print(sep)
        print(f"📋 {label} 策略 · 机会枚举")
        print(sep)
        print(f"✅ 枚举完成 · 共 {total_opps} 条机会")
        if not summary_results:
            return
        print("")
        for res in summary_results:
            version_name = str(res.get("version_dir") or "").strip()
            sn = str(res.get("strategy_name") or strategy_name or "").strip()
            candidates = [
                PathManager.strategy_opportunity_enums(
                    sn or label,
                    use_sampling=False,
                )
                / version_name,
            ]
            report = cls.from_bff_payload({})
            for output_dir in candidates:
                if output_dir.exists():
                    report = cls.load(output_dir)
                    break
            print(f"🔖 strategy={sn or label}")
            print(f"📁 version_dir={res.get('version_dir')}")
            print("")
            for line in report.to_console_lines():
                print(f"   {line}")
            print("")


__all__ = ["EnumeratorReport"]
