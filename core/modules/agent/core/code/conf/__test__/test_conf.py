"""conf 可调常量存在且类型合理。"""

from __future__ import annotations

from core.modules.agent.core.code.conf import (
    PIPELINE_MAX_STEPS,
    PRESENT_MAX_TOKENS,
    PRESENTATION_SCENARIOS,
    PRODUCT_PROVIDER_ID,
    TOOL_AWAIT_SECONDS,
    WORKER_TIMEOUT_SECONDS,
)


def test_conf_knobs() -> None:
    assert PRODUCT_PROVIDER_ID == "ntq"
    assert PIPELINE_MAX_STEPS >= 1
    assert WORKER_TIMEOUT_SECONDS > 0
    assert TOOL_AWAIT_SECONDS > WORKER_TIMEOUT_SECONDS


def test_presentation_scenarios() -> None:
    assert "backtest_price" in PRESENTATION_SCENARIOS
    assert PRESENTATION_SCENARIOS["backtest_price"].startswith("templates/")
    assert PRESENT_MAX_TOKENS >= 512
