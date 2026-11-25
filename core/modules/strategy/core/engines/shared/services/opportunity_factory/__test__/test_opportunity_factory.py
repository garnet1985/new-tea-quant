"""OpportunityFactory：is_opportunity → Opportunity。"""
from __future__ import annotations

from core.modules.data_contract.contracts import DATA_KEY
from core.modules.strategy.core.engines.shared.services.opportunity_factory import (
    OpportunityFactory,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.hooks.base import StrategyHooks
from core.modules.strategy.core.hooks.hook_params import Records, StrategyContext, open_context
from core.modules.strategy.core.hooks.runtime import StrategyHookRuntime

import pytest

pytestmark = pytest.mark.force_run


def _pair(*, rows, settings_dict=None, items=None):
    settings = StrategySettings.from_dict(settings_dict or {})
    settings.apply_defaults()
    base_key = settings.data.base_data_key or DATA_KEY.STOCK_KLINE_DAILY
    packed = dict(items or {})
    if rows is not None:
        packed[base_key] = rows
    ctx = open_context(
        strategy_key="demo",
        settings=settings,
        sample_list=["600000.SH"],
    )
    records = Records(
        entity_id="600000.SH",
        entity_info={"id": "600000.SH", "name": "demo"},
        items=packed,
        base_data_key=base_key,
    )
    return ctx, records, settings


def test_from_hit_requires_base_bar() -> None:
    _, records, settings = _pair(rows=[])
    assert OpportunityFactory.from_hit(records, settings) is None

    _, records, settings = _pair(rows=[{"date": "20240102", "close": 10.0}])
    opp = OpportunityFactory.from_hit(records, settings)
    assert opp is not None
    assert opp.stock.id == "600000.SH"
    assert opp.record_of_today["close"] == 10.0
    assert opp.signal_snapshot.get("close") == 10.0
    assert "date" not in opp.signal_snapshot


def test_resolve_copies_captures_on_true() -> None:
    class Hit(StrategyHooks):
        def is_opportunity(self, ctx: StrategyContext, records: Records) -> bool:
            _ = records
            ctx.capture("rsi", 28.5)
            ctx.capture("pe_percentile", 12.0)
            ctx.state["scratch"] = 1
            return True

    ctx, records, settings = _pair(rows=[{"date": "20240102", "close": 10.0}])
    runtime = StrategyHookRuntime(Hit(), strategy_name="demo", settings=settings)
    opp = OpportunityFactory.resolve(runtime, ctx, records)
    assert opp is not None
    assert opp.signal_snapshot["rsi"] == 28.5
    assert opp.signal_snapshot["pe_percentile"] == 12.0
    assert opp.signal_snapshot["close"] == 10.0
    assert ctx.state["scratch"] == 1
    assert ctx.take_captures() == {}


def test_resolve_discards_captures_on_false() -> None:
    class Miss(StrategyHooks):
        def is_opportunity(self, ctx: StrategyContext, records: Records) -> bool:
            _ = records
            ctx.capture("rsi", 28.5)
            return False

    ctx, records, settings = _pair(rows=[{"date": "20240102", "close": 10.0}])
    runtime = StrategyHookRuntime(Miss(), strategy_name="demo", settings=settings)
    assert OpportunityFactory.resolve(runtime, ctx, records) is None
    assert ctx.take_captures() == {}


def test_resolve_requires_strict_true() -> None:
    class TruthyButNotTrue(StrategyHooks):
        def is_opportunity(self, ctx: StrategyContext, records: Records) -> bool:
            _ = (ctx, records)
            return 1  # type: ignore[return-value]

    class Hit(StrategyHooks):
        def is_opportunity(self, ctx: StrategyContext, records: Records) -> bool:
            _ = (ctx, records)
            return True

    ctx, records, settings = _pair(rows=[{"date": "20240102", "close": 10.0}])

    truthy = StrategyHookRuntime(
        TruthyButNotTrue(), strategy_name="demo", settings=settings
    )
    assert OpportunityFactory.resolve(truthy, ctx, records) is None

    hit = StrategyHookRuntime(Hit(), strategy_name="demo", settings=settings)
    opp = OpportunityFactory.resolve(hit, ctx, records)
    assert opp is not None
    assert opp.record_of_today["close"] == 10.0
    assert opp.signal_snapshot.get("close") == 10.0


def test_as_of_uses_last_base_row_only() -> None:
    _, records, settings = _pair(
        rows=[
            {"date": "20240102", "close": 9.0, "rsi14": 40.0},
            {"date": "20240103", "close": 10.0, "rsi14": 18.5},
        ]
    )
    opp = OpportunityFactory.from_hit(records, settings)
    assert opp is not None
    assert opp.signal_snapshot["close"] == 10.0
    assert opp.signal_snapshot["rsi14"] == 18.5
    assert 9.0 not in opp.signal_snapshot.values()


def test_as_of_adds_required_last_row_prefixed() -> None:
    finance = DATA_KEY.STOCK_FINANCE_QUARTERLY
    _, records, settings = _pair(
        rows=None,
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
    opp = OpportunityFactory.from_hit(records, settings)
    assert opp is not None
    assert opp.signal_snapshot["close"] == 10.0
    assert "raw" not in opp.signal_snapshot
    assert opp.signal_snapshot[f"{finance}.netprofit"] == 2.5
    assert 1.0 not in opp.signal_snapshot.values()


def test_user_capture_overrides_as_of_same_key() -> None:
    class Hit(StrategyHooks):
        def is_opportunity(self, ctx: StrategyContext, records: Records) -> bool:
            _ = records
            ctx.capture("close", 99.0)
            ctx.capture("rsi", 28.5)
            return True

    ctx, records, settings = _pair(rows=[{"date": "20240102", "close": 10.0, "rsi14": 18.0}])
    runtime = StrategyHookRuntime(Hit(), strategy_name="demo", settings=settings)
    opp = OpportunityFactory.resolve(runtime, ctx, records)
    assert opp is not None
    assert opp.signal_snapshot["close"] == 99.0
    assert opp.signal_snapshot["rsi"] == 28.5
    assert opp.signal_snapshot["rsi14"] == 18.0
