"""Tests for chart layer viz_role catalog."""

from core.bff.APIs.strategy.helpers.chart_layer_catalog import (
    VIZ_EVENT_PINS,
    VIZ_LINKED_OHLCV,
    VIZ_MACRO_STEP,
    VIZ_STATE_LANE,
    date_to_quarter,
    quarter_to_end_date,
    resolve_viz_role,
)


def test_resolve_known_roles():
    assert resolve_viz_role("stock.kline.weekly") == VIZ_LINKED_OHLCV
    assert resolve_viz_role("macro.gdp") == VIZ_MACRO_STEP
    assert resolve_viz_role("stock.st_periods") == VIZ_STATE_LANE
    assert resolve_viz_role("stock.finance.quarterly") == VIZ_EVENT_PINS
    assert resolve_viz_role("stock.kline.daily") is None


def test_quarter_helpers():
    assert date_to_quarter("20240615") == "2024Q2"
    assert quarter_to_end_date("2024Q1") == "20240331"
    assert quarter_to_end_date("2024Q4") == "20241231"
