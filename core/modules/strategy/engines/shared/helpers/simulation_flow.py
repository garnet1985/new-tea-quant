#!/usr/bin/env python3
"""模拟 flow 共用：在 preprocess 阶段准备 ``StrategySimulationSettings`` 并生成落盘快照。"""

from __future__ import annotations

from typing import Any, Dict

from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
    StrategySettingsView,
)
from core.modules.strategy.engines.shared.data_classes.strategy_settings.simulation_settings import (
    StrategySimulationSettings,
)


def prepare_simulation_settings(
    base_settings: StrategySettingsView,
) -> StrategySimulationSettings:
    """``apply_defaults`` + 校验；失败时 ``ValueError``。"""
    sim = base_settings.simulation_settings
    sim.apply_defaults()
    report = sim.validate()
    report.raise_if_critical()
    return sim


def simulation_effective_snapshot(sim: StrategySimulationSettings) -> Dict[str, Any]:
    """写入 ``0_metadata.json`` 等：已解析、可读的执行假设（与 worker 行为一致）。"""
    return {
        "template": sim.template,
        "monitor_price_model": sim.monitor_price_model.value,
        "buy_price_model": sim.buy_price_model.value,
        "sell_price_model": sim.sell_price_model.value,
        "slippage_buy_bps": sim.slippage_buy_bps,
        "slippage_sell_bps": sim.slippage_sell_bps,
        "edges_no_next_bar": sim.edges_no_next_bar,
        "allow_buy_at_limit_up": sim.allow_buy_at_limit_up,
        "allow_sell_at_limit_down": sim.allow_sell_at_limit_down,
        "edges": {
            "no_next_bar": sim.edges_no_next_bar,
            "allow_buy_at_limit_up": sim.allow_buy_at_limit_up,
            "allow_sell_at_limit_down": sim.allow_sell_at_limit_down,
        },
        "extreme_same_bar_order": sim.extreme_same_bar_order.value,
        "extreme_same_bar_random_seed": sim.extreme_same_bar_random_seed,
        "skip_investment_when": list(sim.skip_investment_when),
        "max_participation_rate": sim.max_participation_rate,
        "participation_on_exceed": sim.participation_on_exceed,
        "liquidity": {
            "max_participation_rate": sim.max_participation_rate,
            "participation_on_exceed": sim.participation_on_exceed,
        },
    }


__all__ = ["prepare_simulation_settings", "simulation_effective_snapshot"]
