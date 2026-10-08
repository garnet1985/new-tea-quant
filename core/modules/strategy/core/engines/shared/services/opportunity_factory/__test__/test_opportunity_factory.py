"""OpportunityFactory：has_opportunity → Opportunity。"""
from __future__ import annotations

from core.modules.data_contract.contracts import DATA_KEY
from core.modules.strategy.core.engines.shared.services.opportunity_factory import (
    OpportunityFactory,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.hooks.base import StrategyHooks
from core.modules.strategy.core.hooks.hook_params import StrategyContext
from core.modules.strategy.core.hooks.runtime import StrategyHookRuntime

import pytest

pytestmark = pytest.mark.force_run


def _ctx(*, rows):
    settings = StrategySettings.from_dict({})
    settings.apply_defaults()
    base = StrategyContext.assemble(
        strategy_key="demo",
        settings=settings,
        stock_list=["600000.SH"],
        entity_id="600000.SH",
        entity_info={"id": "600000.SH", "name": "demo"},
    )
    return StrategyContext.fill(
        base,
        now="20240102",
        items={DATA_KEY.STOCK_KLINE_DAILY: rows},
        entity_id="600000.SH",
        entity_info={"id": "600000.SH", "name": "demo"},
    )


def test_from_hit_requires_base_bar() -> None:
    ctx = _ctx(rows=[])
    assert OpportunityFactory.from_hit(ctx) is None

    ctx = _ctx(rows=[{"date": "20240102", "close": 10.0}])
    opp = OpportunityFactory.from_hit(ctx)
    assert opp is not None
    assert opp.stock.id == "600000.SH"
    assert opp.record_of_today["close"] == 10.0
    assert opp.signal_snapshot.get("close") == 10.0
    assert "date" not in opp.signal_snapshot


def test_resolve_copies_captures_on_true() -> None:
    class Hit(StrategyHooks):
        def has_opportunity(self, ctx: StrategyContext) -> bool:
            ctx.capture("rsi", 28.5)
            ctx.capture("pe_percentile", 12.0)
            ctx.remember("scratch", 1)
            return True

    settings = StrategySettings.from_dict({})
    settings.apply_defaults()
    ctx = _ctx(rows=[{"date": "20240102", "close": 10.0}])
    runtime = StrategyHookRuntime(Hit(), strategy_name="demo", settings=settings)
    opp = OpportunityFactory.resolve(runtime, ctx)
    assert opp is not None
    assert opp.signal_snapshot["rsi"] == 28.5
    assert opp.signal_snapshot["pe_percentile"] == 12.0
    assert opp.signal_snapshot["close"] == 10.0
    assert ctx.recall("scratch") == 1
    assert ctx.take_captures() == {}


def test_resolve_discards_captures_on_false() -> None:
    class Miss(StrategyHooks):
        def has_opportunity(self, ctx: StrategyContext) -> bool:
            ctx.capture("rsi", 28.5)
            return False

    settings = StrategySettings.from_dict({})
    settings.apply_defaults()
    ctx = _ctx(rows=[{"date": "20240102", "close": 10.0}])
    runtime = StrategyHookRuntime(Miss(), strategy_name="demo", settings=settings)
    assert OpportunityFactory.resolve(runtime, ctx) is None
    assert ctx.take_captures() == {}


def test_resolve_requires_strict_true() -> None:
    class TruthyButNotTrue(StrategyHooks):
        def has_opportunity(self, ctx: StrategyContext) -> bool:
            _ = ctx
            return 1  # type: ignore[return-value]

    class Hit(StrategyHooks):
        def has_opportunity(self, ctx: StrategyContext) -> bool:
            _ = ctx
            return True

    settings = StrategySettings.from_dict({})
    settings.apply_defaults()
    ctx = _ctx(rows=[{"date": "20240102", "close": 10.0}])

    truthy = StrategyHookRuntime(
        TruthyButNotTrue(), strategy_name="demo", settings=settings
    )
    assert OpportunityFactory.resolve(truthy, ctx) is None

    hit = StrategyHookRuntime(Hit(), strategy_name="demo", settings=settings)
    opp = OpportunityFactory.resolve(hit, ctx)
    assert opp is not None
    assert opp.record_of_today["close"] == 10.0
    assert opp.signal_snapshot.get("close") == 10.0


def _ctx_with(*, settings_dict, items):
    settings = StrategySettings.from_dict(settings_dict)
    settings.apply_defaults()
    base = StrategyContext.assemble(
        strategy_key="demo",
        settings=settings,
        stock_list=["600000.SH"],
        entity_id="600000.SH",
        entity_info={"id": "600000.SH", "name": "demo"},
    )
    return StrategyContext.fill(
        base,
        now="20240103",
        items=items,
        entity_id="600000.SH",
        entity_info={"id": "600000.SH", "name": "demo"},
    )


def test_as_of_uses_last_base_row_only() -> None:
    ctx = _ctx(
        rows=[
            {"date": "20240102", "close": 9.0, "rsi14": 40.0},
            {"date": "20240103", "close": 10.0, "rsi14": 18.5},
        ]
    )
    opp = OpportunityFactory.from_hit(ctx)
    assert opp is not None
    assert opp.signal_snapshot["close"] == 10.0
    assert opp.signal_snapshot["rsi14"] == 18.5
    assert 9.0 not in opp.signal_snapshot.values()


def test_as_of_adds_required_last_row_prefixed() -> None:
    finance = DATA_KEY.STOCK_FINANCE_QUARTERLY
    ctx = _ctx_with(
        settings_dict={
            "data": {
                "base": {"data_key": DATA_KEY.STOCK_KLINE_DAILY},
                "required": [{"data_key": finance}],
            }
        },
        items={
            DATA_KEY.STOCK_KLINE_DAILY: [
                {"date": "20240103", "close": 10.0, "raw": {"close": 11.0}}
            ],
            finance: [
                {"date": "20231231", "netprofit": 1.0},
                {"date": "20240331", "netprofit": 2.5, "name": "skip"},
            ],
        },
    )
    opp = OpportunityFactory.from_hit(ctx)
    assert opp is not None
    assert opp.signal_snapshot["close"] == 10.0
    assert "raw" not in opp.signal_snapshot
    assert opp.signal_snapshot[f"{finance}.netprofit"] == 2.5
    assert 1.0 not in opp.signal_snapshot.values()


def test_user_capture_overrides_as_of_same_key() -> None:
    class Hit(StrategyHooks):
        def has_opportunity(self, ctx: StrategyContext) -> bool:
            ctx.capture("close", 99.0)
            ctx.capture("rsi", 28.5)
            return True

    settings = StrategySettings.from_dict({})
    settings.apply_defaults()
    ctx = _ctx(rows=[{"date": "20240102", "close": 10.0, "rsi14": 18.0}])
    runtime = StrategyHookRuntime(Hit(), strategy_name="demo", settings=settings)
    opp = OpportunityFactory.resolve(runtime, ctx)
    assert opp is not None
    assert opp.signal_snapshot["close"] == 99.0
    assert opp.signal_snapshot["rsi"] == 28.5
    assert opp.signal_snapshot["rsi14"] == 18.0
