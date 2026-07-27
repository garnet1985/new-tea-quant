"""``execution_panel`` 由快照 ``result_report`` 派生。"""

from core.modules.strategy_legacy.launcher.workbench_execution_panel import (
    build_execution_panel_from_result_report,
)


def test_execution_panel_enum_from_enum_metrics():
    rr = {
        "enum": {
            "enumMetrics": {"totalOpportunities": 23206, "totalStocks": 5596},
            "enumerator_output_dir": "7",
        }
    }
    panel = build_execution_panel_from_result_report(rr)
    assert panel["enum"]["opportunities"] == 23206


def test_execution_panel_price_step_includes_enum_and_price():
    rr = {
        "price_factor": {
            "priceMetrics": {"winRate": 78.7, "avgRoi": 15.0},
        },
        "enum": {
            "enumMetrics": {"totalOpportunities": 140},
            "enumerator_output_dir": "36",
        },
    }
    panel = build_execution_panel_from_result_report(rr)
    assert panel["enum"]["opportunities"] == 140
    assert panel["price"]["winRate"] == 78.7
    assert panel["price"]["roi"] == 15.0


def test_execution_panel_capital_from_portfolio_metrics():
    rr = {
        "portfolio": {
            "capitalMetrics": {
                "totalProfit": 1000.0,
                "initialCapital": 100000.0,
                "finalEquity": 101000.0,
                "totalReturnPct": 1.0,
            }
        }
    }
    panel = build_execution_panel_from_result_report(rr)
    cap = panel["capital"]
    assert cap["profit"] == 1000.0
    assert cap["initialCapital"] == 100000.0
    assert cap["endCapital"] == 101000.0
    assert cap["retPct"] == 1.0
