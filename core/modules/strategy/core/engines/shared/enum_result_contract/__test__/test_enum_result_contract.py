"""EnumResult / EnumResultsManager 基本往返与查询。"""
from __future__ import annotations

from pathlib import Path

import pytest

from core.modules.strategy.core.engines.shared.data_class.investment.enums import (
    InvestmentResult,
    Lifecycle,
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
from core.modules.strategy.core.engines.shared.data_class.investment.investment import (
    Investment,
)
from core.modules.strategy.core.engines.shared.enum_result_contract import (
    CompletedGoal,
    EnumResult,
    EnumResultsManager,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.services.artifacts import (
    EntityInvestmentCsv,
    EnumerateStore,
    GoalAchievementCsv,
    GoalAchievementRow,
    InvestmentRow,
)

pytestmark = pytest.mark.force_run


def _result(**kwargs) -> EnumResult:
    base = dict(
        entity_id="000001.SZ",
        investment_id="1",
        trigger_date="20240102",
        trigger_price=10.0,
        trigger_price_raw=10.0,
        trigger_price_hfq=10.0,
        entry_date="20240103",
        entry_price=10.5,
        entry_price_raw=10.5,
        entry_price_hfq=10.5,
        exit_date="20240105",
        exit_price=11.0,
        exit_price_raw=11.0,
        exit_price_hfq=11.0,
        exit_reason="take_profit",
        lifecycle="complete",
        result="win",
        weighted_roi=0.05,
        holding_days=2,
        completed_goals=(
            CompletedGoal(
                name="win20%",
                date="20240105",
                price=11.0,
                price_raw=11.0,
                price_hfq=11.0,
                exit_ratio=1.0,
                profit=0.5,
                weighted_profit=0.5,
                reason="take_profit",
                roi=0.05,
            ),
        ),
        signal_snapshot={"rsi": 28.0},
    )
    base.update(kwargs)
    return EnumResult(**base)


def _investment() -> Investment:
    settings = StrategySettings.from_dict({})
    settings.apply_defaults()
    opp = Opportunity(
        stock=StockInfo(id="600000.SH", name="浦发银行"),
        record_of_today={},
        trigger_date="20240102",
        trigger_price=10.0,
        trigger_price_raw=10.1,
        trigger_price_hfq=10.2,
        market_profile="china_a_stock",
        meta=OpportunityMeta(opportunity_id="7"),
        signal_snapshot={"rsi": 31.0},
        metadata={Opportunity.STATUS_AT_TRIGGER_KEY: ["st"]},
    )
    inv = Investment.create_from_opportunity(
        opp, settings=settings, open_dates=("20240102", "20240103")
    )
    inv.lifecycle = Lifecycle.COMPLETE
    inv.runtime_state.entry = EnterState(
        date="20240103",
        price=10.5,
        price_raw=10.6,
        price_hfq=10.7,
        at_limit=False,
        bar_volume=1000.0,
    )
    inv.runtime_state.exit_info = ExitState(
        date="20240104",
        price=11.0,
        price_raw=11.1,
        price_hfq=11.2,
        reason="stop_loss",
        at_limit=True,
    )
    inv.runtime_state.holding.days = 1
    inv.runtime_state.outcome = OutcomeState(
        result=InvestmentResult.LOSS,
        weighted_roi=-0.1,
    )
    inv.completed_goals.append(
        {
            "name": "loss10%",
            "date": "20240104",
            "price": 11.0,
            "price_raw": 11.1,
            "price_hfq": 11.2,
            "exit_ratio": 1.0,
            "profit": -1.0,
            "weighted_profit": -1.0,
            "reason": "stop_loss",
            "roi": -0.1,
        }
    )
    return inv


def test_json_roundtrip_keeps_nested_goals_and_snapshot() -> None:
    original = _result(stock_status_at_trigger=("st",), enter_at_limit=False)
    restored = EnumResult.from_dict(original.to_dict())
    assert restored == original
    assert restored.completed_goals[0].name == "win20%"
    assert restored.signal_snapshot == {"rsi": 28.0}


def test_from_dict_accepts_goal_name_alias() -> None:
    row = EnumResult.from_dict(
        {
            "investment_id": "1",
            "completed_goals": [{"goal_name": "expiration", "date": "20240110", "reason": "expired"}],
        },
        entity_id="000488.SZ",
    )
    assert row.entity_id == "000488.SZ"
    assert row.completed_goals[0].name == "expiration"


def test_from_investment_drops_runtime_and_keeps_fill() -> None:
    inv = _investment()
    row = EnumResult.from_investment(inv)
    assert row.entity_id == "600000.SH"
    assert row.investment_id == "7"
    assert row.entry_date == "20240103"
    assert row.exit_reason == "stop_loss"
    assert row.lifecycle == "complete"
    assert row.result == "loss"
    assert row.weighted_roi == pytest.approx(-0.1)
    assert row.stock_status_at_trigger == ("st",)
    assert row.signal_snapshot == {"rsi": 31.0}
    assert row.completed_goals[0].name == "loss10%"
    assert row.enter_at_limit is False
    assert row.exit_at_limit is True
    dumped = row.to_dict()
    assert "settings" not in dumped
    assert "pending_exit" not in dumped
    assert "last_bar" not in dumped


def test_to_opportunity_hides_outcome() -> None:
    opp = _result(weighted_roi=0.4, result="win").to_opportunity()
    assert opp.stock.id == "000001.SZ"
    assert opp.trigger_date == "20240102"
    assert opp.meta.opportunity_id == "1"
    dumped = opp.to_dict()
    assert "weighted_roi" not in dumped
    assert "entry_date" not in dumped
    assert dumped.get("result") in (None, "")


def test_manager_persist_and_scoped_queries(tmp_path: Path) -> None:
    manager = EnumResultsManager.at(tmp_path)
    filled = _result()
    aborted = _result(
        investment_id="2",
        entry_date="",
        entry_price=0.0,
        exit_date="",
        lifecycle="complete",
        result="",
        weighted_roi=0.0,
        completed_goals=(),
        signal_snapshot={},
    )
    pending = _result(
        entity_id="000002.SZ",
        investment_id="9",
        entry_date="20240201",
        lifecycle="open",
        result="",
        completed_goals=(),
    )
    manager.accept("000001.SZ", [filled, aborted])
    manager.accept("000002.SZ", [pending])
    paths = manager.persist()
    assert len(paths) == 2
    assert (tmp_path / "entities" / "000001.SZ.json").is_file()

    other = EnumResultsManager.at(tmp_path)
    assert [row.investment_id for row in other.filled(["000001.SZ"])] == ["1"]
    assert [row.investment_id for row in other.completed(["000001.SZ"])] == ["1", "2"]
    assert [row.investment_id for row in other.for_entities(["000002.SZ"])] == ["9"]
    assert other.filled(["000002.SZ"])[0].lifecycle == "open"
    assert other.completed(["000002.SZ"]) == []
    assert other.filled([]) == []


def test_manager_csv_fallback_without_json(tmp_path: Path) -> None:
    EnumerateStore.at(tmp_path).write_investments(
        EntityInvestmentCsv(
            entity_id="600000.SH",
            rows=[
                InvestmentRow(
                    investment_id="csv-7",
                    trigger_date="20240102",
                    entry_date="20240103",
                    entry_price_raw=10.6,
                    lifecycle="complete",
                    stock_status_at_trigger=("st",),
                )
            ],
        )
    )
    EnumerateStore.at(tmp_path).write_goals(
        GoalAchievementCsv(
            entity_id="600000.SH",
            rows=[
                GoalAchievementRow(
                    investment_id="csv-7",
                    goal_name="take_profit",
                    date="20240110",
                    price=11.0,
                    exit_ratio=1.0,
                    reason="take_profit",
                )
            ],
        )
    )
    loaded = EnumResultsManager.at(tmp_path).results("600000.SH")
    assert len(loaded) == 1
    assert loaded[0].investment_id == "csv-7"
    assert loaded[0].stock_status_at_trigger == ("st",)
    assert loaded[0].completed_goals[0].name == "take_profit"


def test_manager_accept_investment_and_skip_empty_file(tmp_path: Path) -> None:
    manager = EnumResultsManager.at(tmp_path)
    manager.accept("600000.SH", [_investment()])
    manager.accept("000001.SZ", [])
    written = manager.persist()
    assert [path.name for path in written] == ["600000.SH.json"]
    loaded = EnumResultsManager.at(tmp_path).results("600000.SH")
    assert loaded[0].investment_id == "7"
    assert loaded[0].is_filled()
    assert EnumResultsManager.at(tmp_path).results("000001.SZ") == ()
