"""全仓 _settle 路径应写入 sell_at_limit_down。"""
from core.modules.market_profile import get_market_profile
from core.modules.strategy.engines.shared.data_classes.opportunity import Opportunity
from core.modules.strategy.engines.shared.data_classes.strategy_settings.simulation_settings import (
    StrategySimulationSettings,
)


def test_settle_stamps_sell_at_limit_down():
    profile = get_market_profile("china_a_stock")
    sim = StrategySimulationSettings.from_strategy_root(
        {"simulation": {"template": "standard"}}
    )
    opp = Opportunity(
        stock={"id": "000001.SZ"},
        record_of_today={"date": "20240102", "close": 10.0},
        stock_id="000001.SZ",
        buy_price=10.0,
        buy_date="20240102",
    )
    prev_bar = {"date": "20240101", "close": 10.0}
    opp._settle(
        "20240102",
        9.0,
        "expiration",
        -0.1,
        market_profile=profile,
        prev_bar=prev_bar,
    )
    assert opp.completed_targets
    assert "sell_at_limit_down" in opp.completed_targets[0]
