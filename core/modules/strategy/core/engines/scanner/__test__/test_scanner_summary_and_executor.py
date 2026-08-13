"""Scanner summary / tradability 标注。"""
from __future__ import annotations

import pytest

from core.modules.strategy.core.engines.scanner.helpers.tradability import (
    annotate_enter_at_limit,
    opportunity_enter_at_limit,
)
from core.modules.strategy.core.engines.scanner.report_manager import ScanSummary
from core.modules.strategy.core.engines.shared.data_class.opportunity import (
    Opportunity,
    StockInfo,
)

pytestmark = pytest.mark.force_run


def _opp(
    stock_id: str,
    *,
    at_limit: bool | None = None,
) -> Opportunity:
    opp = Opportunity(
        stock=StockInfo(id=stock_id, name=stock_id),
        record_of_today={"date": "20240110", "close": 11.0, "pre_close": 10.0},
        trigger_date="20240110",
        trigger_price=11.0,
    )
    if at_limit is not None:
        opp.metadata["enter_at_limit"] = at_limit
    return opp


def test_scan_summary_counts_limit_up() -> None:
    summary = ScanSummary.from_opportunities(
        [
            _opp("600000.SH", at_limit=True),
            _opp("600000.SH", at_limit=False),
            _opp("000001.SZ", at_limit=True),
        ]
    ).to_dict()

    assert summary["total_opportunities"] == 3
    assert summary["total_stocks"] == 2
    assert sorted(summary["stocks_with_opportunities"]) == ["000001.SZ", "600000.SH"]
    assert summary["at_limit_up_count"] == 2


def test_annotate_enter_at_limit_sets_metadata() -> None:
    opp = Opportunity(
        stock=StockInfo(id="600000.SH", name="x"),
        record_of_today={"date": "20240110", "close": 11.0, "pre_close": 10.0},
        trigger_date="20240110",
        trigger_price=11.0,
    )
    klines = [
        {
            "date": "20240110",
            "open": 11.0,
            "high": 11.0,
            "low": 11.0,
            "close": 11.0,
            "pre_close": 10.0,
        }
    ]
    annotate_enter_at_limit(
        opp,
        market_profile="china_a_stock",
        klines=klines,
        scan_date="20240110",
    )
    assert opportunity_enter_at_limit(opp) is True
