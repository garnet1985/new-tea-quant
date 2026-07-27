"""机会总体报告（overall_report.json）—— CMD / UI / DB 同一契约。"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, TextIO, TYPE_CHECKING

from core.infra.cmd_layout import CmdLayout
from core.modules.strategy.core.engines.shared.services.simulation_output.file_names import (
    OVERALL_REPORT_FILE,
)
from core.modules.strategy.core.engines.shared.data_class.investment import Lifecycle
from core.modules.strategy.core.helpers.statistics import StatisticsHelper
from core.modules.strategy.core.engines.enumerator.common.report_manager.opportunity_metrics import (
    OpportunityCountBuckets,
    TimingDispersion,
    TradabilityMetrics,
)
from core.modules.strategy.core.engines.enumerator.common.report_manager.report_scan import (
    EnumCsvScan,
)


@dataclass
class OverallSummary:
    """机会总体指标（磁盘 snake_case）。"""

    total_opportunities: int = 0
    total_stocks: int = 0
    trigger_stocks: int = 0
    trigger_ratio: float = 0.0
    avg_per_stock: float = 0.0
    completed_count: int = 0
    unfinished_count: int = 0
    completed_ratio: float = 0.0
    opportunity_buckets: OpportunityCountBuckets = field(
        default_factory=OpportunityCountBuckets
    )
    timing: TimingDispersion = field(default_factory=TimingDispersion)
    tradability: TradabilityMetrics = field(default_factory=TradabilityMetrics)
    percentile_labels: List[str] = field(default_factory=list)
    percentile_values: List[float] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "total_opportunities": self.total_opportunities,
            "total_stocks": self.total_stocks,
            "trigger_stocks": self.trigger_stocks,
            "trigger_ratio": self.trigger_ratio,
            "avg_per_stock": self.avg_per_stock,
            "completed_count": self.completed_count,
            "unfinished_count": self.unfinished_count,
            "completed_ratio": self.completed_ratio,
            "percentile_labels": list(self.percentile_labels),
            "percentile_values": list(self.percentile_values),
        }
        payload.update(self.opportunity_buckets.to_dict())
        payload.update(self.timing.to_dict())
        payload.update(self.tradability.to_dict())
        return payload

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "OverallSummary":
        data = raw or {}
        return cls(
            total_opportunities=int(data.get("total_opportunities") or 0),
            total_stocks=int(data.get("total_stocks") or 0),
            trigger_stocks=int(data.get("trigger_stocks") or 0),
            trigger_ratio=float(data.get("trigger_ratio") or 0.0),
            avg_per_stock=float(data.get("avg_per_stock") or 0.0),
            completed_count=int(data.get("completed_count") or 0),
            unfinished_count=int(data.get("unfinished_count") or 0),
            completed_ratio=float(data.get("completed_ratio") or 0.0),
            opportunity_buckets=OpportunityCountBuckets.from_dict(data),
            timing=TimingDispersion.from_dict(data),
            tradability=TradabilityMetrics.from_dict(data),
            percentile_labels=[str(x) for x in (data.get("percentile_labels") or [])],
            percentile_values=[
                float(v or 0.0) for v in (data.get("percentile_values") or [])
            ],
        )


@dataclass
class OverallReport:
    """机会总体报告稿（文件 / DB / presenter 同一契约）。"""

    OVERALL_REPORT_FILE = OVERALL_REPORT_FILE

    strategy_key: str = ""
    strategy_path: str = ""
    version_id: int = 0
    execution_mode: str = ""
    backtest_period: Dict[str, str] = field(default_factory=dict)
    summary: OverallSummary = field(default_factory=OverallSummary)
    created_at: str = ""

    @classmethod
    def build_from_scan(cls, scan: EnumCsvScan) -> "OverallReport":
        investments = scan.all_investments
        completed = [
            row for row in investments if row.lifecycle == Lifecycle.COMPLETE.value
        ]
        total = max(0, int(scan.total_entities))
        trigger_stocks = sum(
            1 for rows in scan.investments_by_entity.values() if rows
        )
        total_opportunities = len(investments)
        per_stock_counts = [
            len(rows) for rows in scan.investments_by_entity.values()
        ]
        zero_count = max(0, total - len(per_stock_counts))
        all_counts = list(per_stock_counts) + ([0] * zero_count)
        hit_counts = [float(c) for c in per_stock_counts if c > 0]
        percentile_labels, percentile_values = OpportunityCountBuckets.percentiles(
            hit_counts
        )

        summary = OverallSummary(
            total_opportunities=total_opportunities,
            total_stocks=total,
            trigger_stocks=trigger_stocks,
            trigger_ratio=StatisticsHelper.calculate_trigger_ratio(
                trigger_stocks, total
            ),
            avg_per_stock=round(
                StatisticsHelper.calculate_avg_per_stock(
                    total_opportunities, trigger_stocks
                ),
                2,
            ),
            completed_count=len(completed),
            unfinished_count=total_opportunities - len(completed),
            completed_ratio=StatisticsHelper.calculate_completed_ratio(
                len(completed), total_opportunities
            ),
            opportunity_buckets=OpportunityCountBuckets.build(
                all_counts,
                total_stocks=total,
                target_bucket_count=5,
            ),
            timing=TimingDispersion.compute(scan.investments_by_entity),
            tradability=TradabilityMetrics.compute(investments),
            percentile_labels=percentile_labels,
            percentile_values=percentile_values,
        )
        return cls(
            strategy_key=scan.strategy_key,
            strategy_path=scan.strategy_path,
            version_id=scan.version_id,
            execution_mode=scan.execution_mode,
            backtest_period=dict(scan.backtest_period or {}),
            summary=summary,
            created_at=datetime.now().isoformat(),
        )

    @classmethod
    def build(
        cls,
        output_dir: Path,
        *,
        strategy_key: str = "",
        version_id: int = 0,
        total_entities: Optional[int] = None,
    ) -> "OverallReport":
        scan = EnumCsvScan.collect(
            output_dir,
            total_entities=total_entities,
            strategy_key=strategy_key,
            version_id=version_id,
        )
        return cls.build_from_scan(scan)

    @classmethod
    def load(cls, output_dir: Path) -> "OverallReport":
        path = output_dir / cls.OVERALL_REPORT_FILE
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def save(self, output_dir: Path) -> Path:
        path = output_dir / self.OVERALL_REPORT_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return path

    def present(self, stream: Optional[TextIO] = None) -> None:
        """CMD presenter：banner + 机会结论（只读本对象）。"""
        out = stream or sys.stdout
        summary = self.summary
        icon = CmdLayout.icon.get
        period = self.backtest_period or {}
        start = str(period.get("start_date") or "")
        end = str(period.get("end_date") or "")

        CmdLayout.title.print_banner(f"{icon('search')} 枚举报告", stream=out)
        print(
            f"{icon('gear')} {self.strategy_key or '-'} "
            f"v{self.version_id}  "
            f"{icon('calendar')} {start}~{end}  "
            f"{icon('blue_dot')} {self.execution_mode or '-'}  "
            f"entities={summary.total_stocks}",
            file=out,
            flush=True,
        )
        print(
            f"   path={self.strategy_path or self.strategy_key or '-'}",
            file=out,
            flush=True,
        )

        total = max(0, int(summary.total_stocks))
        triggered = max(0, int(summary.trigger_stocks))
        opportunities = max(0, int(summary.total_opportunities))
        completed = max(0, int(summary.completed_count))
        buckets = summary.opportunity_buckets
        timing = summary.timing
        tradability = summary.tradability

        CmdLayout.separator.print_line(width=60, stream=out)
        CmdLayout.title.print_section(f"{icon('target')} 机会概览", stream=out)
        print(
            f"{icon('rocket')} 机会总数 {opportunities}（共 {total} 只股票）",
            file=out,
            flush=True,
        )
        print(
            f"{icon('success')} 机会完整度: {completed}/{opportunities} "
            f"({summary.completed_ratio * 100:.1f}%)",
            file=out,
            flush=True,
        )
        print(
            f"{icon('green_dot')} 触发机会的股票占比: {triggered}/{total} "
            f"({summary.trigger_ratio * 100:.1f}%)",
            file=out,
            flush=True,
        )
        print(
            f"{icon('chart')} 平均每股产生机会数: {summary.avg_per_stock:.2f}",
            file=out,
            flush=True,
        )

        if buckets.labels:
            CmdLayout.title.print_section(
                f"{icon('bar_chart')} 每股机会数分布 "
                f"[{buckets.min_count}~{buckets.max_count}] "
                f"（{max(1, buckets.bucket_count)} 档）",
                stream=out,
            )
            CmdLayout.bar_chart.print(
                [
                    (
                        f"{label} 次",
                        buckets.stock_counts[idx]
                        if idx < len(buckets.stock_counts)
                        else 0,
                    )
                    for idx, label in enumerate(buckets.labels)
                ],
                title="",
                width=24,
                stream=out,
            )

        CmdLayout.title.print_section(f"{icon('warning')} 可交易性", stream=out)
        print(
            f"🔺 涨停无法买入: {tradability.buy_at_limit_up_count}/"
            f"{tradability.buy_tradability_sample_count} "
            f"({tradability.limit_up_buy_ratio}%)",
            file=out,
            flush=True,
        )
        print(
            f"🔻 跌停无法卖出: {tradability.sell_at_limit_down_count}/"
            f"{tradability.sell_tradability_sample_count} "
            f"({tradability.limit_down_sell_ratio}%)",
            file=out,
            flush=True,
        )

        CmdLayout.title.print_section(f"{icon('clock')} 节奏与分散度", stream=out)
        print(
            f"⏱️ 平均每股机会间隔: {timing.mean_gap} 天",
            file=out,
            flush=True,
        )
        print(
            f"⌛ 平均每股机会持续: {timing.mean_duration} 天",
            file=out,
            flush=True,
        )
        print(
            f"📏 机会分散度: SD {timing.std_gap} 天 · CV {timing.cv} · "
            f"{timing.dispersion_conclusion or '—'}",
            file=out,
            flush=True,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_key": self.strategy_key,
            "strategy_path": self.strategy_path,
            "version_id": self.version_id,
            "execution_mode": self.execution_mode,
            "backtest_period": dict(self.backtest_period or {}),
            "summary": self.summary.to_dict(),
            "created_at": self.created_at,
        }

    def to_ui_dict(self) -> Dict[str, Any]:
        """UI / BFF：``enumMetrics`` camelCase + backtest_period。"""
        s = self.summary
        b = s.opportunity_buckets
        t = s.timing
        tr = s.tradability
        out: Dict[str, Any] = {
            "enumMetrics": {
                "totalOpportunities": s.total_opportunities,
                "totalStocks": s.total_stocks,
                "triggerStocks": s.trigger_stocks,
                "triggerRatio": round(s.trigger_ratio * 100.0, 1),
                "avgPerStock": s.avg_per_stock,
                "completedRatio": round(s.completed_ratio * 100.0, 1),
                "completedCount": s.completed_count,
                "unfinishedCount": s.unfinished_count,
                "meanGap": t.mean_gap,
                "meanDuration": t.mean_duration,
                "stdGap": t.std_gap,
                "cv": t.cv,
                "dispersionConclusion": t.dispersion_conclusion,
                "percentileLabels": list(s.percentile_labels),
                "percentileValues": list(s.percentile_values),
                "opportunityCountMin": b.min_count,
                "opportunityCountMax": b.max_count,
                "opportunityCountBucketCount": b.bucket_count,
                "opportunityCountLabels": list(b.labels),
                "opportunityCountStockCounts": list(b.stock_counts),
                "opportunityCountStockRatios": list(b.stock_ratios),
                "buyAtLimitUpCount": tr.buy_at_limit_up_count,
                "buyTradabilitySampleCount": tr.buy_tradability_sample_count,
                "limitUpBuyRatio": tr.limit_up_buy_ratio,
                "sellAtLimitDownCount": tr.sell_at_limit_down_count,
                "sellTradabilitySampleCount": tr.sell_tradability_sample_count,
                "limitDownSellRatio": tr.limit_down_sell_ratio,
            }
        }
        if self.backtest_period.get("start_date") and self.backtest_period.get(
            "end_date"
        ):
            out["backtest_period"] = dict(self.backtest_period)
        return out

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "OverallReport":
        data = raw or {}
        summary_raw = data.get("summary")
        if not isinstance(summary_raw, dict):
            raise ValueError("overall_report 缺少 summary 对象")
        return cls(
            strategy_key=str(data.get("strategy_key") or ""),
            strategy_path=str(data.get("strategy_path") or ""),
            version_id=int(data.get("version_id") or 0),
            execution_mode=str(data.get("execution_mode") or ""),
            backtest_period=dict(data.get("backtest_period") or {}),
            summary=OverallSummary.from_dict(summary_raw),
            created_at=str(data.get("created_at") or ""),
        )


class OverallReportHandle:
    """ReportManager.overall 门面。"""

    def __init__(self, manager: "ReportManager") -> None:
        self._manager = manager
        self._report: Optional[OverallReport] = None

    def build_from_scan(self, scan: EnumCsvScan) -> "OverallReportHandle":
        self._report = OverallReport.build_from_scan(scan)
        return self

    def build(self, *, total_entities: Optional[int] = None) -> "OverallReportHandle":
        self._report = OverallReport.build(
            self._manager.output_dir,
            strategy_key=self._manager.strategy_key,
            version_id=self._manager.version_id,
            total_entities=total_entities,
        )
        return self

    def save(self) -> Path:
        if self._report is None:
            self.build()
        assert self._report is not None
        return self._report.save(self._manager.output_dir)

    def load(self) -> Dict[str, Any]:
        return OverallReport.load(self._manager.output_dir).to_dict()

    def present(self, stream: Optional[TextIO] = None) -> None:
        OverallReport.load(self._manager.output_dir).present(stream=stream)


if TYPE_CHECKING:
    from core.modules.strategy.core.engines.enumerator.common.report_manager.report_manager import (
        ReportManager,
    )


__all__ = [
    "OverallSummary",
    "OverallReport",
    "OverallReportHandle",
]
