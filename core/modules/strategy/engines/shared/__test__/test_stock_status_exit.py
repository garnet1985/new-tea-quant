"""退市强平：stock_status:delisted + 最后可交易 bar 定价。"""
from core.modules.strategy.engines.shared.data_classes.opportunity import Opportunity
from core.modules.strategy.engines.shared.data_classes.strategy_settings.simulation_settings import (
    StrategySimulationSettings,
)
from core.modules.strategy.engines.shared.data_classes.strategy_settings.stock_status_risk_settings import (
    StockStatusRiskManagementSettings,
)
from core.modules.strategy.engines.shared.helpers.stock_status_exit import (
    STOCK_STATUS_REASON_DELISTED,
    apply_stock_status_risk_management,
    should_force_exit_delisted,
    stock_status_reason,
)
from core.modules.strategy.engines.shared.helpers.stock_status_risk_context import (
    StockStatusRiskRuntimeContext,
)
from core.modules.strategy.enums import OpportunityStatus


def _sim() -> StrategySimulationSettings:
    return StrategySimulationSettings.from_strategy_root(
        {"simulation": {"template": "deterministic"}}
    )


def test_should_force_exit_on_delist_date():
    stock = {"id": "600000.SH", "delist_date": "20240615"}
    assert should_force_exit_delisted(stock, "20240614") is False
    assert should_force_exit_delisted(stock, "20240615") is True
    assert should_force_exit_delisted(stock, "20240620") is True


def test_should_ignore_sentinel_delist_date():
    stock = {"id": "600000.SH", "delist_date": "0"}
    assert should_force_exit_delisted(stock, "20240615") is False


def _ctx(
    *,
    stock=None,
    rules=None,
    tiers=None,
    delisted_exit_price="last_tradable_close",
):
    settings = StockStatusRiskManagementSettings(
        rules=tuple(rules or ()),
        delisted_exit_price=delisted_exit_price,
    )
    return StockStatusRiskRuntimeContext(
        settings=settings,
        tier_periods=tiers or {"st": [], "star_st": []},
        stock_meta=stock or {},
    )


def test_force_exit_uses_prev_bar_price_and_date():
    sim = _sim()
    opp = Opportunity(
        stock={"id": "600000.SH", "delist_date": "20240615"},
        record_of_today={},
        buy_date="20240102",
        buy_price=10.0,
        status=OpportunityStatus.ACTIVE.value,
    )
    current = {"date": "20240615", "open": 1.0, "close": 1.0}
    prev = {"date": "20240614", "open": 2.0, "close": 3.0, "high": 3.0, "low": 2.0}
    ctx = _ctx(stock=opp.stock)
    assert apply_stock_status_risk_management(opp, sim, current, ctx, prev_bar=prev)
    assert opp.sell_reason == STOCK_STATUS_REASON_DELISTED
    assert opp.sell_date == "20240614"
    assert opp.sell_price == 3.0
    assert opp.status in (OpportunityStatus.WIN.value, OpportunityStatus.LOSS.value)
    assert opp.completed_targets[0]["reason"] == STOCK_STATUS_REASON_DELISTED


def test_check_targets_triggers_delist_before_other_rules():
    sim = _sim()
    opp = Opportunity(
        stock={"id": "600000.SH", "delist_date": "20240615"},
        record_of_today={},
        buy_date="20240102",
        buy_price=10.0,
        protect_loss_active=True,
    )
    goal = {"protect_loss": {"ratio": -0.01}}
    current = {"date": "20240615", "close": 100.0, "open": 100.0}
    prev = {"date": "20240614", "close": 5.0, "open": 5.0}
    done = opp.check_targets(
        sim,
        current_kline=current,
        goal_config=goal,
        prev_bar=prev,
    )
    assert done is True
    assert opp.sell_reason == STOCK_STATUS_REASON_DELISTED
    assert opp.sell_date == "20240614"


def test_st_rule_fires_once_on_first_day_in_period():
    sim = _sim()
    from core.modules.strategy.engines.shared.data_classes.strategy_settings.stock_status_risk_settings import (
        StockStatusRiskRule,
    )

    opp = Opportunity(
        stock={"id": "600000.SH"},
        record_of_today={},
        buy_date="20240102",
        buy_price=10.0,
        status=OpportunityStatus.ACTIVE.value,
    )
    ctx = _ctx(
        rules=[StockStatusRiskRule(name="st", close_invest=True)],
        tiers={
            "st": [{"st_level": "st", "start_date": "20240301", "end_date": "20240331"}],
            "star_st": [],
        },
    )
    bar = {"date": "20240301", "close": 8.0, "open": 8.0}
    assert apply_stock_status_risk_management(opp, sim, bar, ctx)
    assert opp.sell_reason == stock_status_reason("st")
    assert "st" in (opp.triggered_stock_status_names or [])
