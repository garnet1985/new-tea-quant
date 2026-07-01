"""枚举报告统计编排（跨模式）。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from core.modules.strategy.core.engines.shared.data_classes.report_templates import EnumeratorReportTemplate
from core.modules.strategy.core.helpers.opportunity_csv import OpportunityCsvHelper
from core.modules.strategy.core.helpers.statistics import StatisticsHelper


class EnumeratorReportStatistics:
    """从 opportunities 目录聚合枚举报告。"""

    @staticmethod
    def from_opportunities(
        opportunities: List[Dict[str, Any]],
        total_stocks_hint: Optional[int] = None,
    ) -> EnumeratorReportTemplate:
        if not opportunities:
            return EnumeratorReportTemplate(
                total_opportunities=0,
                total_stocks=total_stocks_hint or 0,
                trigger_stocks=0,
                completed_count=0,
                unfinished_count=0,
            )

        grouped = StatisticsHelper.group_by_stock(opportunities)
        trigger_stocks = len(grouped)

        completed_count = 0
        unfinished_count = 0
        for opp in opportunities:
            outcome = opp.get("outcome", "")
            if outcome == "completed":
                completed_count += 1
            else:
                unfinished_count += 1

        stock_rows: List[Dict[str, Any]] = []
        for stock_id, opps in sorted(grouped.items()):
            stock_rows.append({"stock_id": stock_id, "opportunity_count": len(opps)})

        total_opportunities = len(opportunities)
        total_stocks = total_stocks_hint or trigger_stocks

        return EnumeratorReportTemplate(
            total_opportunities=total_opportunities,
            total_stocks=total_stocks,
            trigger_stocks=trigger_stocks,
            completed_count=completed_count,
            unfinished_count=unfinished_count,
            stock_rows=stock_rows,
        )

    @staticmethod
    def collect_from_dir(source: Path) -> List[Dict[str, Any]]:
        return OpportunityCsvHelper.collect_from_dir(source)

    @staticmethod
    def compute_from_dir(
        source: Path,
        total_stocks_hint: Optional[int] = None,
    ) -> EnumeratorReportTemplate:
        opportunities = EnumeratorReportStatistics.collect_from_dir(source)
        return EnumeratorReportStatistics.from_opportunities(
            opportunities,
            total_stocks_hint=total_stocks_hint,
        )

    @staticmethod
    def compute_derived_metrics(template: EnumeratorReportTemplate) -> Dict[str, float]:
        return {
            "trigger_ratio": StatisticsHelper.calculate_trigger_ratio(
                template.trigger_stocks,
                template.total_stocks,
            ),
            "avg_per_stock": StatisticsHelper.calculate_avg_per_stock(
                template.total_opportunities,
                template.trigger_stocks,
            ),
            "completed_ratio": StatisticsHelper.calculate_completed_ratio(
                template.completed_count,
                template.total_opportunities,
            ),
        }

    @staticmethod
    def to_bff_payload(
        template: EnumeratorReportTemplate,
        include_stock_rows: bool = False,
    ) -> Dict[str, Any]:
        payload = template.to_dict()
        payload.update(EnumeratorReportStatistics.compute_derived_metrics(template))
        if not include_stock_rows:
            payload.pop("stock_rows", None)
        return payload


__all__ = ["EnumeratorReportStatistics"]
