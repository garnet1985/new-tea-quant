"""Workbench snapshot DTO：step_status 独立于 result_report hydrate。"""

from core.bff.APIs.strategy.helpers.formatting import workbench_snapshot_to_message


def test_step_status_prefers_disk_row_over_empty_result_report():
    msg = workbench_snapshot_to_message(
        {
            "version": 6,
            "settings_snapshot": {},
            "disk_settings": {},
            "effective_settings": {},
            "execute_settings": {},
            "settings_rev": "abc",
            "result_report": {"enum": {"success": True}},
            "step_status": {
                "enum": {"done": True},
                "price_factor": {"done": True},
                "portfolio": {"done": True},
            },
            "pinned": True,
        }
    )
    assert msg["step_status"] == {
        "enum": {"done": True},
        "price_factor": {"done": True},
        "portfolio": {"done": True},
    }
    assert msg["pinned"] is True


def test_step_status_falls_back_to_result_report_when_row_omits_it():
    msg = workbench_snapshot_to_message(
        {
            "version": 1,
            "result_report": {"enum": {"success": True}},
        }
    )
    assert msg["step_status"]["enum"]["done"] is True
    assert msg["step_status"]["price_factor"]["done"] is False
    assert msg["step_status"]["portfolio"]["done"] is False
