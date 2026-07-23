"""T+1（market profile rules.settlement）：买入当日不触发止盈/止损等卖出判定。"""
from core.modules.market_profile import get_market_profile
from core.modules.strategy.engines.shared.data_classes.investment_state import ScanSignalPhase
from core.modules.strategy.engines.shared.data_classes.opportunity import Opportunity
from core.modules.strategy.engines.shared.data_classes.strategy_settings.simulation_settings import (
    StrategySimulationSettings,
)


def _sim() -> StrategySimulationSettings:
    return StrategySimulationSettings.from_strategy_root(
        {"simulation": {"template": "standard"}}
    )


def _take_profit_goal(ratio: float = 0.05) -> dict:
    return {
        "take_profit": {
            "stages": [
                {
                    "ratio": ratio,
                    "sell_ratio": 1.0,
                    "name": "take_profit_5pct",
                },
            ],
        },
    }


def test_no_target_on_buy_day_t_plus_one():
    sim = _sim()
    profile = get_market_profile("china_a_stock")
    opp = Opportunity(
        stock={"id": "600000.SH"},
        record_of_today={},
        buy_date="20240103",
        buy_price=10.0,
        signal_phase=ScanSignalPhase.ACTIVE.value,
    )
    bar = {"date": "20240103", "open": 10.0, "close": 12.0, "high": 12.0, "low": 10.0}
    opp.check_targets(
        sim,
        current_kline=bar,
        goal_config=_take_profit_goal(),
        market_profile=profile,
    )
    assert not opp.completed_targets
    assert opp.sell_date is None


def test_target_on_day_after_buy():
    sim = _sim()
    profile = get_market_profile("china_a_stock")
    opp = Opportunity(
        stock={"id": "600000.SH"},
        record_of_today={},
        buy_date="20240103",
        buy_price=10.0,
        signal_phase=ScanSignalPhase.ACTIVE.value,
    )
    bar = {"date": "20240104", "open": 11.0, "close": 12.0, "high": 12.0, "low": 11.0}
    opp.check_targets(
        sim,
        current_kline=bar,
        goal_config=_take_profit_goal(),
        market_profile=profile,
    )
    assert len(opp.completed_targets) == 1
    assert opp.completed_targets[0]["date"] == "20240104"
