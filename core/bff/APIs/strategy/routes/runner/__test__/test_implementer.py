"""Tests for strategy runner implementer (normalize + resolve wiring)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.bff.APIs.strategy.routes.runner.implementer import StrategyRunnerImplementer


def test_normalize_step_delegates():
    impl = StrategyRunnerImplementer()
    launcher = MagicMock()
    launcher.normalize_step.side_effect = lambda s: (
        s.lower() if s.lower() in ("enum", "price", "portfolio") else None
    )
    impl._WorkbenchRunLauncher = launcher
    assert impl.normalize_step("PRICE") == "price"
    assert impl.normalize_step("capital") is None


def test_submit_run_resolves_name():
    impl = StrategyRunnerImplementer()
    launcher = MagicMock()
    launcher.submit.return_value = {"is_triggered": True, "job_id": "j1"}
    impl._WorkbenchRunLauncher = launcher
    with patch.object(impl, "resolve_strategy_name", return_value="demo/x"):
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
    launcher = MagicMock()
    launcher.normalize_step.return_value = None
    impl._WorkbenchRunLauncher = launcher
    with patch.object(impl, "resolve_strategy_name", return_value="demo/x"):
        with pytest.raises(ValueError, match="step"):
            impl.get_step_progress(
                strategy_key_or_name="demo/x", step="nope", job_id="j"
            )


def test_trigger_scan_resolves_name():
    impl = StrategyRunnerImplementer()
    trigger = MagicMock(return_value={"is_triggered": True, "job_id": "s1"})
    impl._trigger_strategy_scan_run = trigger
    with patch.object(impl, "resolve_strategy_name", return_value="demo/x"):
        out = impl.trigger_scan(strategy_key_or_name="k", demo=True, force=False)
    assert out["job_id"] == "s1"
    trigger.assert_called_once_with(strategy_name="demo/x", demo=True, force=False)
