"""Tests for strategy runner implementer (normalize + resolve wiring)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.modules.strategy.contracts import WorkbenchStep
from core.bff.APIs.strategy.routes.runner.implementer import StrategyRunnerImplementer


def test_normalize_step():
    assert StrategyRunnerImplementer.normalize_step("enum") == "enum"
    assert StrategyRunnerImplementer.normalize_step("PRICE") == "price"
    assert StrategyRunnerImplementer.normalize_step("portfolio") == "portfolio"
    assert StrategyRunnerImplementer.normalize_step("capital") is None
    assert WorkbenchStep.try_parse("enumerate") is WorkbenchStep.ENUM
    assert StrategyRunnerImplementer.normalize_step("nope") is None


def test_submit_run_resolves_name():
    impl = StrategyRunnerImplementer()
    launcher = MagicMock()
    launcher.submit.return_value = {"is_triggered": True, "job_id": "j1"}
    impl._WorkbenchRunLauncher = launcher
    with patch(
        "core.bff.APIs.strategy.routes.runner.implementer.Strategy.resolve",
        return_value="demo/x",
    ):
        out = impl.submit_run(
            strategy_key_or_name="k",
            step="enum",
            api_settings={"a": 1},
            force_refresh=True,
        )
    assert out["job_id"] == "j1"
    launcher.submit.assert_called_once_with(
        strategy_name="demo/x",
        step="enum",
        api_settings={"a": 1},
        force_refresh=True,
    )


def test_get_step_progress_rejects_bad_step():
    impl = StrategyRunnerImplementer()
    impl._WorkbenchRunLauncher = MagicMock()
    with patch(
        "core.bff.APIs.strategy.routes.runner.implementer.Strategy.resolve",
        return_value="demo/x",
    ):
        with pytest.raises(ValueError, match="step"):
            impl.get_step_progress(
                strategy_key_or_name="demo/x", step="nope", job_id="j"
            )


def test_trigger_scan_resolves_name():
    impl = StrategyRunnerImplementer()
    trigger = MagicMock(return_value={"is_triggered": True, "job_id": "s1"})
    impl._trigger_strategy_scan_run = trigger
    with patch(
        "core.bff.APIs.strategy.routes.runner.implementer.Strategy.resolve",
        return_value="demo/x",
    ):
        out = impl.trigger_scan(strategy_key_or_name="k", demo=True, force=False)
    assert out["job_id"] == "s1"
    trigger.assert_called_once_with(strategy_name="demo/x", demo=True, force=False)
