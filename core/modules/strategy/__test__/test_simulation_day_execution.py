#!/usr/bin/env python3
"""simulation_day_execution 单元测试。"""

from core.modules.strategy.engines.shared.data_classes.opportunity import Opportunity
from core.modules.strategy.engines.shared.data_classes.strategy_settings.simulation_settings import (
    StrategySimulationSettings,
)
from core.modules.strategy.engines.shared.helpers.simulation_day_execution import (
    fill_pending_buys,
    queue_deferred_buy,
    resolve_pending_buys_at_end,
)
from core.modules.strategy.enums import OpportunityStatus


def _sim(**edges) -> StrategySimulationSettings:
    root = {
        "simulation": {
            "template": "deterministic",
            "slippage": {"buy_bps": 0.0, "sell_bps": 0.0},
            "edges": edges or {"no_next_bar": "skip_trade"},
        }
    }
    s = StrategySimulationSettings.from_strategy_root(root)
    s.apply_defaults()
    return s


class TestSimulationDayExecution:
    def test_deferred_buy_fills_on_next_bar(self):
        sim = _sim()
        bar0 = {"date": "20240101", "open": 9.0, "close": 9.5, "high": 10, "low": 9}
        bar1 = {"date": "20240102", "open": 10.2, "close": 10.8, "high": 11, "low": 10}
        opp = Opportunity(
            stock={},
            record_of_today=bar0,
            trigger_date="20240101",
            trigger_price=9.5,
        )
        queue_deferred_buy(opp, signal_bar=bar0)
        assert opp.buy_fill_pending
        assert opp.buy_price == 0.0

        pending, active = [opp], []
        fill_pending_buys(pending, active, bar=bar1, sim=sim)
        assert not pending
        assert len(active) == 1
        assert active[0].buy_date == "20240102"
        assert active[0].buy_price == 10.2
        assert active[0].status == OpportunityStatus.ACTIVE.value

    def test_resolve_pending_skip_trade_removes(self):
        sim = _sim(no_next_bar="skip_trade")
        bar0 = {"date": "20240101", "open": 9.0, "close": 9.5, "high": 10, "low": 9}
        opp = Opportunity(stock={}, record_of_today=bar0, trigger_date="20240101", trigger_price=9.5)
        queue_deferred_buy(opp, signal_bar=bar0)
        pending, active, all_opps = [opp], [], [opp]
        resolve_pending_buys_at_end(pending, active, all_opps, sim=sim)
        assert not pending
        assert not all_opps
