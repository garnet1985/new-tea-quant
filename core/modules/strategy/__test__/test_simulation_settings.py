#!/usr/bin/env python3
"""StrategySimulationSettings 单元测试。"""

from core.modules.strategy.engines.shared.data_classes.strategy_settings.simulation_settings import (
    StrategySimulationSettings,
    TradePriceModel,
)


class TestStrategySimulationSettings:
    def test_deterministic_defaults(self):
        sim = StrategySimulationSettings.from_strategy_root({"simulation": {"template": "deterministic"}})
        sim.apply_defaults()
        assert sim.template == "deterministic"
        assert sim.buy_price_model == TradePriceModel.NEXT_OPEN
        assert sim.sell_price_model == TradePriceModel.CLOSE
        assert sim.slippage_buy_bps == 0.0

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

    def test_allow_at_limit_from_legacy_skip_keys(self):
        sim = StrategySimulationSettings.from_strategy_root(
            {
                "simulation": {
                    "template": "deterministic",
                    "edges": {
                        "skip_limit_up_buy": True,
                        "skip_limit_down_sell": False,
                    },
                }
            }
        )
        sim.apply_defaults()
        assert sim.allow_buy_at_limit_up is False
        assert sim.allow_sell_at_limit_down is True

    def test_allow_at_limit_explicit(self):
        sim = StrategySimulationSettings.from_strategy_root(
            {
                "simulation": {
                    "template": "deterministic",
                    "edges": {
                        "allow_buy_at_limit_up": False,
                        "allow_sell_at_limit_down": True,
                    },
                }
            }
        )
        assert sim.allow_buy_at_limit_up is False
        assert sim.allow_sell_at_limit_down is True
