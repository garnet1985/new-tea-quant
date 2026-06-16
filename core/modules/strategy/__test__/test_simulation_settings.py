#!/usr/bin/env python3
"""StrategySimulationSettings 单元测试。"""

from core.modules.strategy.engines.shared.data_classes.strategy_settings.simulation_settings import (
    StrategySimulationSettings,
    TradePriceModel,
    simulation_template_defaults_payload,
)


class TestStrategySimulationSettings:
    def test_standard_defaults(self):
        sim = StrategySimulationSettings.from_strategy_root({"simulation": {"template": "standard"}})
        sim.apply_defaults()
        assert sim.template == "standard"
        assert sim.buy_price_model == TradePriceModel.NEXT_OPEN
        assert sim.sell_price_model == TradePriceModel.CLOSE
        assert sim.allow_buy_at_limit_up is False
        assert sim.skip_investment_when == ()
        assert sim.max_participation_rate == 0.1
        assert sim.participation_on_exceed == "clip"

    def test_strict_skips_st(self):
        sim = StrategySimulationSettings.from_strategy_root({"simulation": {"template": "strict"}})
        sim.apply_defaults()
        assert sim.template == "strict"
        assert sim.skip_investment_when == ("st", "star_st")
        assert sim.allow_buy_at_limit_up is False
        assert sim.participation_on_exceed == "skip"

    def test_ideal_allows_limit_trades(self):
        sim = StrategySimulationSettings.from_strategy_root({"simulation": {"template": "ideal"}})
        sim.apply_defaults()
        assert sim.allow_buy_at_limit_up is True
        assert sim.skip_investment_when == ()

    def test_unknown_template_fails(self):
        sim = StrategySimulationSettings.from_strategy_root(
            {"simulation": {"template": "deterministic"}}
        )
        report = sim.validate()
        assert report.has_critical_errors()

    def test_preset_with_skip_investment_when_fails(self):
        sim = StrategySimulationSettings.from_strategy_root(
            {
                "simulation": {
                    "template": "strict",
                    "skip_investment_when": ["st"],
                }
            }
        )
        report = sim.validate()
        assert report.has_critical_errors()
    def test_custom_requires_models(self):
        sim = StrategySimulationSettings.from_strategy_root(
            {
                "simulation": {
                    "template": "custom",
                    "monitor_price_model": "close",
                    "buy_price_model": "close",
                    "sell_price_model": "close",
                }
            }
        )
        report = sim.validate()
        assert not report.has_critical_errors()

    def test_custom_missing_models_fails(self):
        sim = StrategySimulationSettings.from_strategy_root({"simulation": {"template": "custom"}})
        report = sim.validate()
        assert report.has_critical_errors()

    def test_extreme_template(self):
        sim = StrategySimulationSettings.from_strategy_root({"simulation": {"template": "extreme"}})
        sim.apply_defaults()
        assert sim.monitor_price_model.value == "extreme"
        assert sim.buy_price_model == TradePriceModel.EXTREME

    def test_removed_skip_limit_keys_fail_validation(self):
        sim = StrategySimulationSettings.from_strategy_root(
            {
                "simulation": {
                    "template": "custom",
                    "monitor_price_model": "close",
                    "buy_price_model": "next_open",
                    "sell_price_model": "close",
                    "edges": {"skip_limit_up_buy": True},
                }
            }
        )
        report = sim.validate()
        assert report.has_critical_errors()

    def test_removed_mark_unfinished_fails_validation(self):
        sim = StrategySimulationSettings.from_strategy_root(
            {
                "simulation": {
                    "template": "custom",
                    "monitor_price_model": "close",
                    "buy_price_model": "next_open",
                    "sell_price_model": "close",
                    "edges": {"no_next_bar": "mark_unfinished"},
                }
            }
        )
        report = sim.validate()
        assert report.has_critical_errors()

    def test_preset_template_rejects_detail_overrides(self):
        sim = StrategySimulationSettings.from_strategy_root(
            {
                "simulation": {
                    "template": "standard",
                    "edges": {"allow_buy_at_limit_up": False},
                }
            }
        )
        report = sim.validate()
        assert report.has_critical_errors()

    def test_preset_template_rejects_skip_investment_when(self):
        sim = StrategySimulationSettings.from_strategy_root(
            {
                "simulation": {
                    "template": "standard",
                    "skip_investment_when": ["st"],
                }
            }
        )
        report = sim.validate()
        assert report.has_critical_errors()

    def test_allow_at_limit_explicit_requires_custom(self):
        sim = StrategySimulationSettings.from_strategy_root(
            {
                "simulation": {
                    "template": "custom",
                    "monitor_price_model": "close",
                    "buy_price_model": "next_open",
                    "sell_price_model": "close",
                    "edges": {
                        "allow_buy_at_limit_up": False,
                        "allow_sell_at_limit_down": True,
                    },
                }
            }
        )
        report = sim.validate()
        assert not report.has_critical_errors()
        assert sim.allow_buy_at_limit_up is False
        assert sim.allow_sell_at_limit_down is True

    def test_template_defaults_payload_strict(self):
        payload = simulation_template_defaults_payload("strict")
        assert payload["skip_investment_when"] == ["st", "star_st"]
        assert payload["edges"]["allow_buy_at_limit_up"] is False
        assert payload["liquidity"]["max_participation_rate"] == 0.1
        assert payload["liquidity"]["participation_on_exceed"] == "skip"

    def test_custom_liquidity_parsed(self):
        sim = StrategySimulationSettings.from_strategy_root(
            {
                "simulation": {
                    "template": "custom",
                    "monitor_price_model": "close",
                    "buy_price_model": "next_open",
                    "sell_price_model": "close",
                    "liquidity": {
                        "max_participation_rate": 0.2,
                        "participation_on_exceed": "skip",
                    },
                }
            }
        )
        report = sim.validate()
        assert not report.has_critical_errors()
        assert sim.max_participation_rate == 0.2
        assert sim.participation_on_exceed == "skip"

    def test_preset_rejects_liquidity_override(self):
        sim = StrategySimulationSettings.from_strategy_root(
            {"simulation": {"template": "standard", "liquidity": {"max_participation_rate": 0.5}}}
        )
        report = sim.validate()
        assert report.has_critical_errors()

    def test_default_execution_mode_entity_timeline(self):
        sim = StrategySimulationSettings.from_strategy_root({"simulation": {"template": "standard"}})
        sim.apply_defaults()
        assert sim.execution_mode == "entity_timeline"

    def test_calendar_slice_execution_mode(self):
        sim = StrategySimulationSettings.from_strategy_root(
            {
                "simulation": {
                    "template": "standard",
                    "execution_mode": "calendar_slice",
                    "slice_open_days": 63,
                }
            }
        )
        sim.apply_defaults()
        assert sim.execution_mode == "calendar_slice"
        assert sim.slice_open_days == 63
        report = sim.validate()
        assert not report.has_critical_errors()

    def test_invalid_execution_mode_fails(self):
        sim = StrategySimulationSettings.from_strategy_root(
            {"simulation": {"template": "standard", "execution_mode": "legacy"}}
        )
        report = sim.validate()
        assert report.has_critical_errors()

    def test_slice_open_days_too_small_fails(self):
        sim = StrategySimulationSettings.from_strategy_root(
            {
                "simulation": {
                    "template": "standard",
                    "execution_mode": "calendar_slice",
                    "slice_open_days": 2,
                }
            }
        )
        report = sim.validate()
        assert report.has_critical_errors()
