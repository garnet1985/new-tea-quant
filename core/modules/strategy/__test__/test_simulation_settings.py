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
