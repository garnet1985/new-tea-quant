"""滚动测试按钮：三层完成且 rolling.py 可用才可点。"""
from core.modules.strategy.core.engines.rolling.readiness import describe_rolling_button


def test_button_stays_disabled_until_steps_and_config() -> None:
    missing = describe_rolling_button(
        steps_ready=False,
        config_state="missing",
        has_report=False,
        parent_version_id="",
        window_count=0,
    )
    assert missing["enabled"] is False
    assert "回测" in missing["tooltip"]
    assert "rolling.py" in missing["tooltip"]

    steps_only = describe_rolling_button(
        steps_ready=True,
        config_state="missing",
        has_report=False,
        parent_version_id="1",
        window_count=0,
    )
    assert steps_only["enabled"] is False
    assert "rolling.py" in steps_only["tooltip"]
    assert "回测" not in steps_only["tooltip"]


def test_button_enables_when_ready_and_keeps_report_flag() -> None:
    ready = describe_rolling_button(
        steps_ready=True,
        config_state="ok",
        has_report=True,
        parent_version_id="3",
        window_count=2,
    )
    assert ready["enabled"] is True
    assert ready["tooltip"] == ""
    assert ready["has_report"] is True
    assert ready["parent_version_id"] == "3"
    assert ready["window_count"] == 2

    invalid = describe_rolling_button(
        steps_ready=True,
        config_state="invalid",
        has_report=False,
        parent_version_id="3",
        window_count=0,
    )
    assert invalid["enabled"] is False
    assert invalid["reason"] == "rolling_invalid"
    assert "窗口无法使用" in invalid["tooltip"]
