"""RunProgressReporter phased progress tests."""
from __future__ import annotations

from unittest.mock import patch

from core.modules.backtest_engine.core.shared.modes import BacktestMode
from core.modules.backtest_engine.core.shared.progress import (
    RunPhase,
    RunProgressReporter,
)


def test_mark_phase_uses_shared_steps() -> None:
    reporter = RunProgressReporter(
        task_name="demo",
        run_mode=BacktestMode.ENTITY_BASED.value,
        enable_progress_display=False,
    )
    prep = reporter.mark_phase(RunPhase.PREP)
    assert prep.percent == 0

    plan = reporter.mark_phase(RunPhase.PLAN)
    assert plan.percent == 25

    reporter.set_execute_total(10)
    reporter.mark_phase(RunPhase.EXECUTE)
    execute_mid = reporter.mark_execute_unit(5)
    assert execute_mid.percent == 62.5

    finish = reporter.mark_phase(RunPhase.FINISH)
    assert finish.percent == 100.0


def test_enable_progress_display_false_skips_output() -> None:
    reporter = RunProgressReporter(
        task_name="demo",
        run_mode=BacktestMode.SLICE_BASED.value,
        enable_progress_display=False,
    )
    with patch("builtins.print") as print_mock:
        reporter.mark_phase(RunPhase.PREP)
        reporter.set_execute_total(2)
        reporter.mark_phase(RunPhase.EXECUTE)
        reporter.mark_execute_unit(1)

    print_mock.assert_not_called()


def test_report_from_payload_invokes_hook() -> None:
    calls: list[int] = []

    def hook(completed: int) -> None:
        calls.append(completed)

    RunProgressReporter.report_from_payload(
        {"_engine_on_execute_unit_done": hook},
        3,
    )
    assert calls == [3]


def test_report_from_payload_ignores_missing_hook() -> None:
    RunProgressReporter.report_from_payload({}, 1)
