"""portfolio.allocation.opportunity_selection：可省略，写了才校验。"""
from __future__ import annotations

import pytest

from core.modules.strategy.core.engines.shared.services.strategy_settings import (
    StrategySettings,
)

pytestmark = pytest.mark.force_run


def _usable(selection):
    payload = {"portfolio": {"allocation": {}}}
    if selection is not None:
        payload["portfolio"]["allocation"]["opportunity_selection"] = selection
    return StrategySettings.to_usable(payload)


def test_omitted_selection_keeps_arrival_order() -> None:
    settings = _usable(None)
    alloc = settings.portfolio.allocation
    assert alloc.opportunity_selection == ()
    assert alloc.opportunity_selection_mode == ""
    assert "opportunity_selection" not in settings.portfolio.portfolio["allocation"]


def test_empty_selection_is_arrival_order() -> None:
    settings = _usable([])
    assert settings.portfolio.allocation.opportunity_selection_mode == ""


def test_order_rules_normalize_case_and_src() -> None:
    settings = _usable(
        [
            {"close": "desc"},
            {"pe": "ASC", "src": " gdp "},
        ]
    )
    rules = settings.portfolio.allocation.opportunity_selection
    assert settings.portfolio.allocation.opportunity_selection_mode == "order"
    assert rules[0].field == "close"
    assert rules[0].direction == "DESC"
    assert rules[0].snapshot_key("stock.kline.daily") == "close"
    assert rules[1].src == "gdp"
    assert rules[1].snapshot_key("stock.kline.daily") == "gdp.pe"
    stored = settings.portfolio.portfolio["allocation"]["opportunity_selection"]
    assert stored[0] == {"close": "DESC"}
    assert stored[1] == {"pe": "ASC", "src": "gdp"}


def test_weight_rules_keep_sign_and_base_src() -> None:
    settings = _usable(
        [
            {"close": 20, "src": "stock.kline.daily"},
            {"pe": -80},
        ]
    )
    alloc = settings.portfolio.allocation
    assert alloc.opportunity_selection_mode == "weight"
    assert alloc.opportunity_selection[0].weight == 20
    assert alloc.opportunity_selection[0].snapshot_key("stock.kline.daily") == "close"
    assert alloc.opportunity_selection[1].weight == -80
    assert alloc.opportunity_selection[1].snapshot_key("stock.kline.daily") == "pe"


def test_all_zero_weights_mean_unconfigured() -> None:
    settings = _usable([{"close": 0}, {"pe": 0.0}])
    assert settings.portfolio.allocation.opportunity_selection == ()
    assert settings.portfolio.portfolio["allocation"]["opportunity_selection"] == []


@pytest.mark.parametrize(
    "selection, message",
    [
        ("close", "须为 list"),
        ([{"close": "DESC", "pe": "ASC"}], "恰好写一个字段"),
        ([{"close": "DESC"}, {"pe": 80}], "不能同时写"),
        ([{"close": "SIDEWAYS"}], "须为 ASC、DESC 或数字权重"),
        ([{"close": True}], "须为 ASC、DESC 或数字权重"),
        ([{"src": "gdp"}], "恰好写一个字段"),
        ([{"close": "DESC"}, {"close": "ASC"}], "重复字段"),
        ([{"close": 20, "src": ""}], "src 须为非空字符串"),
    ],
)
def test_invalid_selection_rejected(selection, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        _usable(selection)
