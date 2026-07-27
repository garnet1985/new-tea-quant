"""``execution_panel`` 由快照 ``result_report`` 派生。"""

from core.modules.strategy.launcher.workbench_execution_panel import (
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
        "price_factor": {"win_rate": 78.7, "avg_roi": 0.15},
        "enum": {
            "enumMetrics": {"totalOpportunities": 140},
            "enumerator_output_dir": "36",
        },
    }
    panel = build_execution_panel_from_result_report(rr)
    assert panel["enum"]["opportunities"] == 140
    assert panel["price"]["winRate"] == 78.7
    assert panel["price"]["roi"] == 15.0


def test_execution_panel_capital_return_pct_scaled():
    rr = {
        "capital_allocation": {
            "total_profit": 1000.0,
            "initial_capital": 100000.0,
            "final_total_equity": 101000.0,
            "total_return": 0.1006,
        }
    }
    panel = build_execution_panel_from_result_report(rr)
    cap = panel["capital"]
    assert cap["profit"] == 1000.0
    assert cap["initialCapital"] == 100000.0
    assert cap["endCapital"] == 101000.0
    assert cap["retPct"] == 10.06
