"""simulation.skip_investment_when + 枚举 metadata 标签。"""
import json

from core.modules.strategy.engines.shared.data_classes.strategy_settings.simulation_settings import (
    StrategySimulationSettings,
)
from core.modules.strategy.engines.shared.helpers.skip_investment_when import (
    METADATA_TAGS_KEY,
    ROW_SKIP_REASON_KEY,
    active_tags_at_trigger_from_row,
    parse_skip_investment_when,
    should_skip_investment,
    stamp_stock_status_at_trigger,
    stock_status_tags_csv_value,
)
from core.modules.strategy.services.data.output.enumerator_output_service import (
    EnumeratorOutputWriterService,
)
from core.modules.strategy.engines.shared.data_classes.opportunity import Opportunity
from core.modules.strategy.engines.shared.data_classes.strategy_settings.stock_status_risk_settings import (
    StockStatusRiskManagementSettings,
)
from core.modules.strategy.engines.shared.helpers.stock_status_risk_context import (
    StockStatusRiskRuntimeContext,
)


def test_parse_skip_investment_when():
    assert parse_skip_investment_when([]) == ()
    assert parse_skip_investment_when(["st", "star_st"]) == ("st", "star_st")


def test_should_skip_from_metadata():
    row = {
        "metadata": {"stock_status_at_trigger": ["star_st"]},
    }
    assert should_skip_investment(row, ("star_st",)) == "stock_status:star_st"
    assert should_skip_investment(row, ("st",)) is None
    assert should_skip_investment(row, ()) is None


def test_should_skip_from_csv_flat_column():
    row = {METADATA_TAGS_KEY: json.dumps(["st"], ensure_ascii=False)}
    assert active_tags_at_trigger_from_row(row) == ["st"]
    assert should_skip_investment(row, ("st",)) == "stock_status:st"


def test_enumerator_csv_exports_stock_status_column():
    opp = {
        "opportunity_id": "1",
        "trigger_date": "20240301",
        "metadata": {"stock_status_at_trigger": ["st", "star_st"]},
        "completed_targets": [],
    }
    rows, _ = EnumeratorOutputWriterService.build_stock_rows(opportunities=[opp])
    assert len(rows) == 1
    assert rows[0]["stock_status_at_trigger"] == '["st", "star_st"]'
    assert should_skip_investment(rows[0], ("st",)) == "stock_status:st"
    assert stock_status_tags_csv_value(opp) == '["st", "star_st"]'


def test_simulation_settings_skip_property():
    sim = StrategySimulationSettings.from_strategy_root(
        {
            "simulation": {
                "template": "custom",
                "monitor_price_model": "close",
                "buy_price_model": "next_open",
                "sell_price_model": "close",
                "skip_investment_when": ["st"],
            }
        }
    )
    assert sim.skip_investment_when == ("st",)


def test_strict_preset_skip_from_template():
    sim = StrategySimulationSettings.from_strategy_root(
        {"simulation": {"template": "strict"}}
    )
    assert sim.skip_investment_when == ("st", "star_st")


def test_tier_periods_loaded_without_goal_rules():
    """未配置持仓平仓规则时，仍应加载 ST 时段供 skip_investment_when 打标。"""
    settings = StockStatusRiskManagementSettings.from_goal_block(None)
    ctx = StockStatusRiskRuntimeContext.build(
        stock_meta={},
        settings=settings,
        raw_st_periods=[
            {
                "st_level": "STAR_ST",
                "start_date": "20230505",
                "end_date": None,
            }
        ],
    )
    assert ctx.tier_periods["star_st"]
    assert ProjectContext.active_status_tags_at("20240605") == ["star_st"]
    opp = Opportunity(stock={"id": "600766.SH"}, record_of_today={})
    stamp_stock_status_at_trigger(
        opp,
        trade_date="20240605",
        tier_periods=ctx.tier_periods,
    )
    assert opp.metadata["stock_status_at_trigger"] == ["star_st"]
    assert should_skip_investment(opp.to_dict(), ("star_st",)) == "stock_status:star_st"


def test_stamp_at_trigger():
    opp = Opportunity(stock={"id": "600000.SH"}, record_of_today={})
    stamp_stock_status_at_trigger(
        opp,
        trade_date="20240301",
        tier_periods={
            "st": [{"st_level": "st", "start_date": "20240301", "end_date": "20240331"}],
            "star_st": [],
        },
    )
    assert opp.metadata["stock_status_at_trigger"] == ["st"]
    row = opp.to_dict()
    assert should_skip_investment(row, ("st",)) == "stock_status:st"
    assert ROW_SKIP_REASON_KEY not in row
