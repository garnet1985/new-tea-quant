#!/usr/bin/env python3
"""EnumeratorReport.present 使用 summary 内 enumMetrics，不依赖已 prune 的磁盘目录。"""

from core.modules.strategy.engines.simulator.enumerator.shared.report import (
    EnumeratorReport,
)


def test_report_for_present_prefers_summary_enum_metrics():
    em = {
        "totalOpportunities": 23206,
        "totalStocks": 5596,
        "triggerStocks": 1200,
        "triggerRatio": 21.4,
    }
    report, loaded = EnumeratorReport._report_for_present(
        res={
            "strategy_name": "example",
            "enumerator_output_dir": "5",
            "enumMetrics": em,
            "backtest_period": {"start_date": "2023-01-03", "end_date": "2026-01-01"},
        },
        strategy_name="example",
        version_name="5",
    )
    assert loaded is None
    assert report.total_opportunities == 23206
    assert report.total_stocks == 5596
    assert report.trigger_stocks == 1200
