"""枚举落盘走 EnumResultsManager JSON；CSV sidecar 仍写。"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from core.modules.strategy.core.engines.enumerator.common.report_manager.report_scan import (
    _load_investments_by_entity,
)
from core.modules.strategy.core.engines.enumerator.common.report_manager.stock_investments import (
    InvestmentsReport,
)
from core.modules.strategy.core.engines.enumerator.common.state.investment_tracker import (
    InvestmentTracker,
)
from core.modules.strategy.core.engines.shared.data_class.investment.enums import (
    InvestmentResult,
    Lifecycle,
)
from core.modules.strategy.core.engines.shared.data_class.investment.investment import (
    Investment,
)
from core.modules.strategy.core.engines.shared.data_class.investment.investment_state import (
    EnterState,
    ExitState,
    OutcomeState,
)
from core.modules.strategy.core.engines.shared.data_class.opportunity import (
    Opportunity,
    OpportunityMeta,
    StockInfo,
)
from core.modules.strategy.core.engines.shared.enum_result_contract import (
    EnumResultsManager,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.services.artifacts import STOCK_INVESTMENTS_SUFFIX

pytestmark = pytest.mark.force_run


def _investment(entity_id: str = "600000.SH", investment_id: str = "7") -> Investment:
    settings = StrategySettings.from_dict({})
    settings.apply_defaults()
    opp = Opportunity(
        stock=StockInfo(id=entity_id),
        record_of_today={},
        trigger_date="20240102",
        trigger_price=10.0,
        trigger_price_raw=10.1,
        trigger_price_hfq=10.2,
        market_profile="china_a_stock",
        meta=OpportunityMeta(opportunity_id=investment_id),
        signal_snapshot={"rsi": 31.0},
    )
    inv = Investment.create_from_opportunity(
        opp, settings=settings, open_dates=("20240102", "20240103")
    )
    inv.lifecycle = Lifecycle.COMPLETE
    inv.runtime_state.entry = EnterState(date="20240103", price=10.5, price_raw=10.6, price_hfq=10.7)
    inv.runtime_state.exit_info = ExitState(
        date="20240104", price=11.0, price_raw=11.1, price_hfq=11.2, reason="take_profit"
    )
    inv.runtime_state.holding.days = 1
    inv.runtime_state.outcome = OutcomeState(
        result=InvestmentResult.WIN, weighted_roi=0.05
    )
    return inv


def test_flush_writes_json_and_deprecated_csv(tmp_path: Path) -> None:
    tracker = InvestmentTracker(entity_id="600000.SH")
    tracker.completed.append(_investment())
    buffer = InvestmentTracker.buffer_many_for_persist({"600000.SH": tracker})
    assert "investment" in buffer[0]
    assert isinstance(buffer[0]["opportunity"], dict)

    report = InvestmentsReport(SimpleNamespace(output_dir=tmp_path, version_id="1"))
    stats = report.flush_buffered(buffer)
    assert stats["json_files"] == 1
    assert stats["investment_files"] == 1
    assert (tmp_path / "entities" / "600000.SH.json").is_file()
    assert (tmp_path / "entities" / f"600000.SH{STOCK_INVESTMENTS_SUFFIX}").is_file()

    loaded = EnumResultsManager.at(tmp_path).filled(["600000.SH"])
    assert [row.investment_id for row in loaded] == ["7"]
    assert loaded[0].signal_snapshot == {"rsi": 31.0}


def test_enum_report_scan_prefers_json(tmp_path: Path) -> None:
    tracker = InvestmentTracker(entity_id="600000.SH")
    tracker.completed.append(_investment())
    InvestmentsReport(SimpleNamespace(output_dir=tmp_path, version_id="1")).flush_buffered(
        InvestmentTracker.buffer_many_for_persist({"600000.SH": tracker})
    )
    by_entity = _load_investments_by_entity(tmp_path)
    assert list(by_entity) == ["600000.SH"]
    assert by_entity["600000.SH"][0].investment_id == "7"
    assert by_entity["600000.SH"][0].lifecycle == "complete"
