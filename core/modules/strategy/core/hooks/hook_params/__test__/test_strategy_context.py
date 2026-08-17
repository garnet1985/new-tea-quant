"""StrategyContext assemble / fill / refill 主线（钩子入参壳）。"""
from __future__ import annotations

import pytest

from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.hooks.hook_params.strategy_context import (
    StrategyContext,
    StrategyData,
    StrategyInfo,
)

pytestmark = pytest.mark.force_run


def _settings() -> StrategySettings:
    return StrategySettings.from_dict(
        {
            "simulation": {"execution": {"mode": "entity_based"}},
            "data": {"base": {"data_key": "stock.kline.daily"}},
        }
    )


def test_assemble_builds_shell_with_stock_list() -> None:
    ctx = StrategyContext.assemble(
        strategy_key="demo/rsi",
        settings=_settings(),
        stock_list=["000001.SZ", ""],
        strategy_path="/tmp/demo",
    )
    assert ctx.strategy.key == "demo/rsi"
    assert ctx.strategy.path == "/tmp/demo"
    assert list(ctx.data.stock_list) == ["000001.SZ"]
    assert ctx.base_data_key == "stock.kline.daily"


def test_fill_requires_assembled_stock_list() -> None:
    bare = StrategyContext.assemble(
        strategy_key="demo",
        settings=_settings(),
        stock_list=[],
    )
    with pytest.raises(ValueError, match="assemble"):
        StrategyContext.fill(bare, now="20240110", items={})


def test_fill_and_refill_share_custom_and_settings_cache() -> None:
    base = StrategyContext.assemble(
        strategy_key="demo",
        settings=_settings(),
        stock_list=["000001.SZ"],
        custom={"flag": 1},
    )
    d1 = base.effective_settings_dict()
    filled = StrategyContext.fill(base, now="20240110", items={"k": []})
    assert filled.custom is base.custom
    assert filled.data.now == "20240110"
    assert filled.effective_settings_dict() is d1

    filled.refill(now="20240111", items={"k": [1]})
    assert filled.data.now == "20240111"
    assert filled.custom["flag"] == 1


def test_remember_recall_forget() -> None:
    ctx = StrategyContext.assemble(
        strategy_key="demo",
        settings=_settings(),
        stock_list=["000001.SZ"],
    )
    ctx.remember("last_rsi", 28.5)
    assert ctx.recall("last_rsi") == 28.5
    assert ctx.custom["last_rsi"] == 28.5
    assert ctx.recall("missing") is None
    assert ctx.recall("missing", 0) == 0
    ctx.forget("last_rsi")
    assert ctx.recall("last_rsi") is None
    ctx.forget("missing")


def test_fill_shares_captures_bag() -> None:
    base = StrategyContext.assemble(
        strategy_key="demo",
        settings=_settings(),
        stock_list=["000001.SZ"],
    )
    filled = StrategyContext.fill(base, now="20240110", items={"k": []})
    filled.capture("rsi", 12)
    assert base.take_captures() == {"rsi": 12}
    assert filled.take_captures() == {}


def test_refill_without_stock_list_raises() -> None:
    ctx = StrategyContext(
        strategy=StrategyInfo(key="x"),
        settings=_settings(),
        data=StrategyData.build(stock_list=[]),
    )
    with pytest.raises(ValueError, match="assemble"):
        ctx.refill(now="20240110")
