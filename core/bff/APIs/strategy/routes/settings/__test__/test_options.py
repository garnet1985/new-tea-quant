"""Tests for strategy settings option catalogs (V2-04)."""

from __future__ import annotations

from core.bff.APIs.strategy.routes.settings.options import StrategySettingsOptions
from core.modules.strategy.core.engines.shared.services.strategy_settings.simulation_settings.assumption_templates import (
    AssumptionTemplate,
)


def test_portfolio_allocation_modes():
    items = StrategySettingsOptions.items_portfolio()
    values = {row["value"] for row in items}
    assert values == {"equal_capital", "equal_shares", "kelly", "custom"}
    assert all("label" in row for row in items)


def test_sampling_strategies_include_weighted():
    items = StrategySettingsOptions.items_sampling()
    values = {row["value"] for row in items}
    assert "weighted" in values
    assert "uniform" in values


def test_risk_control_tags():
    items = StrategySettingsOptions.items_risk_control()
    values = {row["value"] for row in items}
    assert values == {"st", "star_st"}


def test_simulation_template_defaults_are_nested_tradability():
    items = StrategySettingsOptions.items_simulation()
    by_value = {row["value"]: row for row in items}
    assert "none" not in by_value
    assert AssumptionTemplate.NAMED.issubset(by_value.keys())
    assert "custom" in by_value

    standard = by_value["standard"]["defaults"]
    assert "tradability" in standard
    assert standard["tradability"]["enter_price"] == "touch"
    assert "buy_price_model" not in standard
    assert "skip_investment_when" not in standard

    custom = by_value["custom"]["defaults"]
    assert custom == {}


def test_market_rules_non_empty():
    items = StrategySettingsOptions.items_market_rules()
    assert len(items) >= 1
    assert any(row["value"] == "china_a_stock" for row in items)
