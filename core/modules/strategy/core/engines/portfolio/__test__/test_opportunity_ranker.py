"""opportunity_selection：排序、加权、钩子优先。"""
from __future__ import annotations

from typing import Dict, Sequence, Union

import pytest

from core.modules.strategy.core.engines.portfolio.data_class import PortfolioEvent
from core.modules.strategy.core.engines.portfolio.opportunity_ranker import (
    OpportunityRanker,
)
from core.modules.strategy.core.engines.portfolio.enter_selection import (
    EnterSelection,
    EntrySelector,
)
from core.modules.strategy.core.engines.shared.data_class.opportunity import Opportunity
from core.modules.strategy.core.engines.shared.enum_result_contract import EnumResult
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.hooks.base import StrategyHooks
from core.modules.strategy.core.hooks.hook_params import StrategyContext
from core.modules.strategy.core.hooks.runtime import StrategyHookRuntime

pytestmark = pytest.mark.force_run

_BASE = "stock.kline.daily"


def _opp(oid: str, entity_id: str, snapshot: Dict[str, float]) -> Opportunity:
    return EnumResult(
        entity_id=entity_id,
        investment_id=oid,
        trigger_date="20240102",
        trigger_price=1.0,
        entry_date="20240103",
        entry_price_raw=10.0,
        signal_snapshot=snapshot,
    ).to_opportunity()


def _settings(selection, size: int = 5) -> StrategySettings:
    allocation = {"max_portfolio_size": size}
    if selection is not None:
        allocation["opportunity_selection"] = selection
    return StrategySettings.to_usable(
        {
            "data": {"base": {"data_key": _BASE}},
            "portfolio": {"initial_capital": 1_000_000, "allocation": allocation},
        }
    )


def _pick(selection, opps, *, size: int = 5, held=None) -> list:
    settings = _settings(selection, size)
    return EnterSelection.create(
        settings=settings,
        strategy_name="demo",
        selector=EntrySelector(max_portfolio_size=size),
    ).select_for_date(
        date="20240103",
        available=opps,
        held_entity_ids=set(held or []),
    )


def test_order_sorts_close_then_pe() -> None:
    opps = [
        _opp("a", "S1", {"close": 10, "pe": 5}),
        _opp("b", "S2", {"close": 30, "pe": 9}),
        _opp("c", "S3", {"close": 30, "pe": 2}),
    ]
    picked = _pick([{"close": "DESC"}, {"pe": "ASC"}], opps)
    assert picked == ["S3:c", "S2:b", "S1:a"]


def test_missing_sort_key_sinks() -> None:
    opps = [
        _opp("a", "S1", {}),
        _opp("b", "S2", {"close": 1}),
        _opp("c", "S3", {"close": 5}),
    ]
    picked = _pick([{"close": "DESC"}], opps)
    assert picked == ["S3:c", "S2:b", "S1:a"]


def test_negative_weight_prefers_lower_pe() -> None:
    opps = [
        _opp("high", "S1", {"close": 10, "pe": 50}),
        _opp("low", "S2", {"close": 10, "pe": 5}),
    ]
    picked = _pick([{"close": 20}, {"pe": -80}], opps, size=1)
    assert picked == ["S2:low"]


def test_src_splits_same_field_name() -> None:
    opps = [
        _opp("kline", "S1", {"close": 100, "gdp.close": 1}),
        _opp("macro", "S2", {"close": 1, "gdp.close": 100}),
    ]
    picked = _pick(
        [
            {"close": 20, "src": _BASE},
            {"close": 80, "src": "gdp"},
        ],
        opps,
        size=1,
    )
    assert picked == ["S2:macro"]


def test_same_entity_keeps_better_rank() -> None:
    opps = [
        _opp("weak", "S1", {"close": 1}),
        _opp("other", "S2", {"close": 5}),
        _opp("strong", "S1", {"close": 9}),
    ]
    picked = _pick([{"close": "DESC"}], opps, size=2)
    assert picked == ["S1:strong", "S2:other"]


def test_held_entity_is_excluded_before_ranking() -> None:
    opps = [
        _opp("giant", "S0", {"close": 1000}),
        _opp("low", "S1", {"close": 10}),
        _opp("high", "S2", {"close": 12}),
    ]
    ordered = OpportunityRanker.order(
        opps,
        _settings([{"close": "DESC"}]).portfolio.allocation.opportunity_selection,
        mode="order",
        base_data_key=_BASE,
        held_entity_ids={"S0"},
    )
    assert [EntrySelector.opportunity_selection_key(opp) for opp in ordered] == [
        "S2:high",
        "S1:low",
    ]


def test_held_entity_does_not_take_a_slot() -> None:
    opps = [
        _opp("held", "S1", {"close": 100}),
        _opp("next", "S2", {"close": 1}),
    ]
    picked = _pick([{"close": "DESC"}], opps, size=2, held=["S1"])
    assert picked == ["S2:next"]


def test_hook_ignores_selection() -> None:
    class PickLow(StrategyHooks):
        def has_opportunity(self, ctx: StrategyContext) -> bool:
            return False

        def on_pick_portfolio_member(
            self, ctx: StrategyContext
        ) -> Sequence[Union[Opportunity, str]]:
            return ["low"]

    opps = [
        _opp("low", "S1", {"close": 1}),
        _opp("high", "S2", {"close": 99}),
    ]
    settings = _settings([{"close": "DESC"}], size=1)
    runtime = StrategyHookRuntime(PickLow(), strategy_name="demo", settings=settings)
    events = [
        PortfolioEvent(
            kind="buy", date="20240103", entity_id="S1", investment_id="low", price=1
        ),
        PortfolioEvent(
            kind="buy", date="20240103", entity_id="S2", investment_id="high", price=1
        ),
    ]
    keyed = {
        EntrySelector.selection_key("S1", "low"): opps[0],
        EntrySelector.selection_key("S2", "high"): opps[1],
    }
    filtered = EnterSelection.create(
        settings=settings,
        strategy_name="demo",
        hook_runtime=runtime,
        selector=EntrySelector(max_portfolio_size=1),
    ).apply(events, keyed)
    assert {event.investment_id for event in filtered} == {"low"}
