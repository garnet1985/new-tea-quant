"""PortfolioPipeline / on_pick_portfolio_member / EntrySelector 单测。"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Sequence, Union
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.force_run

from core.modules.strategy.core.enums import SimulateKind
from core.modules.strategy.core.engines.enumerator.shared.report_manager.stock_investments import (
    InvestmentRow,
    StockInvestments,
)
from core.modules.strategy.core.engines.portfolio.data_class import PortfolioEvent
from core.modules.strategy.core.engines.portfolio.enter_selection import (
    EnterSelection,
    EntrySelector,
)
from core.modules.strategy.core.engines.portfolio.pipeline import PortfolioPipeline
from core.modules.strategy.core.engines.price_factor.enum_data import EnumVersionData
from core.modules.strategy.core.engines.shared.data_class.opportunity import Opportunity
from core.modules.strategy.core.engines.shared.services.strategy_settings.portfolio_settings import (
    PortfolioSettings,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.hooks.base import StrategyHooks
from core.modules.strategy.core.hooks.context import DataContext
from core.modules.strategy.core.hooks.runtime import StrategyHookRuntime
from core.modules.strategy.strategy import BackTestPipelines
from core.modules.strategy.core.engines.shared.data_class.simulate_session import SimulateSession


def _opp(oid: str, entity_id: str) -> Opportunity:
    return InvestmentRow(
        investment_id=oid,
        trigger_date="20240102",
        trigger_price=1.0,
        entry_date="20240103",
        entry_price_raw=10.0,
        exit_date="20240110",
        weighted_roi=0.1,
    ).to_opportunity(entity_id)


def _settings_with_max_size(n: int) -> StrategySettings:
    raw = {
        "data": {"base": {"data_key": "stock.kline.daily", "params": {}}},
        "portfolio": {"allocation": {"max_portfolio_size": n}},
    }
    settings = StrategySettings.from_dict(raw)
    settings.apply_defaults()
    return settings


def test_backtest_pipelines_wires_portfolio():
    pipeline = BackTestPipelines[SimulateKind.PORTFOLIO]
    assert pipeline is PortfolioPipeline


def test_load_enum_data_requires_enum_version():
    ctx = SimulateSession(
        strategy_info=SimpleNamespace(
            key="demo",
            unique_relative_path="demo/rsi",
        ),
        fp_res=MagicMock(
            settings_fp="s",
            env_fp="e",
            effective_settings=MagicMock(),
            global_entity_cache=MagicMock(),
            entity_ids=[],
        ),
        kind=SimulateKind.PORTFOLIO,
        enum_version=None,
        steps=[SimulateKind.PORTFOLIO],
    )
    with pytest.raises(ValueError, match="enum_version"):
        PortfolioPipeline.load_enum_data(ctx)


def test_build_events_uses_raw_buy_price_not_qfq(tmp_path: Path):
    StockInvestments(
        entity_id="600000.SH",
        rows=[
            InvestmentRow(
                investment_id="1",
                trigger_date="20240102",
                entry_date="20240103",
                entry_price=10.0,
                entry_price_raw=20.0,
                exit_date="20240110",
                exit_price=11.0,
                exit_price_raw=22.0,
                weighted_roi=0.1,
                lifecycle="complete",
                result="win",
            ),
            InvestmentRow(
                investment_id="2",
                trigger_date="20240102",
                entry_date="20240104",
                entry_price=10.0,
                entry_price_raw=0.0,
                exit_date="20240111",
                weighted_roi=0.2,
                lifecycle="complete",
            ),
        ],
    ).save(tmp_path)

    runtime = MagicMock()
    runtime.entity_ids = ["600000.SH"]
    runtime.market_profile = ""
    runtime.period = SimpleNamespace(start_date="20240101", end_date="20240131")
    data = EnumVersionData(output_dir=tmp_path, version_id="1", runtime=runtime)
    events, opportunities = PortfolioPipeline.build_events(
        data, settings=PortfolioSettings(raw_settings={})
    )
    assert len(events) == 2
    buy, sell = events
    assert buy.price == 20.0
    assert sell.price == 22.0
    dumped = opportunities["1"].to_dict()
    assert "weighted_roi" not in dumped
    assert "result" not in dumped


def test_entry_selector_picks_in_order_within_capacity():
    selector = EntrySelector(max_portfolio_size=2)
    available = [
        _opp("a", "600000.SH"),
        _opp("b", "600001.SH"),
        _opp("c", "600002.SH"),
    ]
    picked = selector.pick_ids(available, held_entity_ids=set())
    assert picked == ["a", "b"]

    picked2 = selector.pick_ids(available, held_entity_ids={"600000.SH"})
    # remaining = 2 - 1 = 1 → 只再接 1 个
    assert picked2 == ["b"]


def test_entry_selector_skips_already_held_entity():
    selector = EntrySelector(max_portfolio_size=5)
    available = [_opp("a", "600000.SH"), _opp("b", "600000.SH"), _opp("c", "600001.SH")]
    assert selector.pick_ids(available, held_entity_ids=set()) == ["a", "c"]


def test_default_enter_selection_respects_max_portfolio_size():
    opps = {
        "a": _opp("a", "600000.SH"),
        "b": _opp("b", "600001.SH"),
        "c": _opp("c", "600002.SH"),
    }
    events = [
        PortfolioEvent(
            kind="buy", date="20240103", entity_id="600000.SH", investment_id="a", price=10.0
        ),
        PortfolioEvent(
            kind="buy", date="20240103", entity_id="600001.SH", investment_id="b", price=10.0
        ),
        PortfolioEvent(
            kind="buy", date="20240103", entity_id="600002.SH", investment_id="c", price=10.0
        ),
        PortfolioEvent(
            kind="sell", date="20240110", entity_id="600000.SH", investment_id="a", price=11.0
        ),
        PortfolioEvent(
            kind="sell", date="20240110", entity_id="600001.SH", investment_id="b", price=11.0
        ),
        PortfolioEvent(
            kind="sell", date="20240110", entity_id="600002.SH", investment_id="c", price=11.0
        ),
    ]
    filtered = EnterSelection.create(
        settings=_settings_with_max_size(2),
        strategy_name="demo",
        selector=EntrySelector(max_portfolio_size=2),
    ).apply(events, opps)
    ids = {e.investment_id for e in filtered}
    assert ids == {"a", "b"}


def test_on_pick_portfolio_member_override_filters_by_id():
    class PickOne(StrategyHooks):
        def scan_opportunity(self, ctx: DataContext):
            return None

        def on_pick_portfolio_member(
            self, ctx: DataContext
        ) -> Sequence[Union[Opportunity, str]]:
            return ["a"]

    opps = {
        "a": _opp("a", "600000.SH"),
        "b": _opp("b", "600001.SH"),
    }
    events = [
        PortfolioEvent(
            kind="buy", date="20240103", entity_id="600000.SH", investment_id="a", price=10.0
        ),
        PortfolioEvent(
            kind="buy", date="20240103", entity_id="600001.SH", investment_id="b", price=10.0
        ),
        PortfolioEvent(
            kind="sell", date="20240110", entity_id="600000.SH", investment_id="a", price=11.0, roi=0.1
        ),
        PortfolioEvent(
            kind="sell", date="20240110", entity_id="600001.SH", investment_id="b", price=12.0, roi=0.2
        ),
    ]
    settings = _settings_with_max_size(10)
    runtime = StrategyHookRuntime(PickOne(), strategy_name="demo", settings=settings)
    filtered = EnterSelection.create(
        settings=settings,
        strategy_name="demo",
        hook_runtime=runtime,
    ).apply(events, opps)
    assert {e.investment_id for e in filtered} == {"a"}
    assert len(filtered) == 2


def test_normalize_selected_ids_rejects_unknown():
    available = [_opp("a", "x")]
    assert EnterSelection.normalize_selected_ids(available, ["a", "ghost", "a"]) == ["a"]
