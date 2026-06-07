"""价格步 progress 切片：enum 仅含 ``enumMetrics`` 时仍应带出正确 ``opportunities``。"""

from core.modules.strategy.execution_manager.workbench_disk_progress import (
    _enum_summary_from_result_report,
    _fed_execution_step_card_slice,
)


def test_enum_summary_reads_total_opportunities_from_enum_metrics():
    rr = {
        "enum": {
            "enumMetrics": {"totalOpportunities": 23206, "totalStocks": 5596},
            "enumerator_output_dir": "7",
        }
    }
    summary = _enum_summary_from_result_report(rr)
    assert summary is not None
    assert summary["opportunities"] == 23206


def test_price_step_progress_card_keeps_enum_opportunity_count(monkeypatch):
    def _fake_fetch(_name, _ver):
        return {
            "result_report": {
                "price_factor": {"win_rate": 78.7, "avg_roi": 0.15},
                "enum": {
                    "enumMetrics": {"totalOpportunities": 140},
                    "enumerator_output_dir": "36",
                },
            }
        }

    monkeypatch.setattr(
        "core.modules.strategy.launcher.workbench.fetch_workbench_by_version",
        _fake_fetch,
    )
    card = _fed_execution_step_card_slice("example", "price", 6)
    assert card["enum"]["opportunities"] == 140
