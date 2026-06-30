"""RunProgressReporter phased progress tests."""
from __future__ import annotations

from unittest.mock import patch

from core.modules.backtest_engine.core.shared.modes import BacktestMode
from core.modules.backtest_engine.core.shared.progress import (
    PHASE_EXECUTE_WEIGHT,
    PHASE_FINISH_WEIGHT,
    PHASE_PLAN_WEIGHT,
    PHASE_PREP_WEIGHT,
    RunPhase,
    RunProgressReporter,
    report_execute_unit_from_context,
)


def test_phase_weights_sum_to_one() -> None:
    total = (
        PHASE_PREP_WEIGHT
        + PHASE_PLAN_WEIGHT
        + PHASE_EXECUTE_WEIGHT
        + PHASE_FINISH_WEIGHT
    )
    assert total == 1.0


def test_mark_phase_advances_percent_floor() -> None:
    reporter = RunProgressReporter(
        task_name="demo",
        run_mode=BacktestMode.ENTITY_BASED.value,
        enable_progress_display=False,
    )
    prep = reporter.mark_phase(RunPhase.PREP)
    assert prep.percent == PHASE_PREP_WEIGHT * 100.0

    plan = reporter.mark_phase(RunPhase.PLAN)
    assert plan.percent == (PHASE_PREP_WEIGHT + PHASE_PLAN_WEIGHT) * 100.0

    reporter.set_execute_total(10)
    reporter.mark_phase(RunPhase.EXECUTE)
    execute_mid = reporter.mark_execute_unit(5)
    expected_floor = (PHASE_PREP_WEIGHT + PHASE_PLAN_WEIGHT) * 100.0
    expected = expected_floor + 0.5 * PHASE_EXECUTE_WEIGHT * 100.0
    assert execute_mid.percent == expected

    finish = reporter.mark_phase(RunPhase.FINISH)
    assert finish.percent == 100.0


def test_enable_progress_display_false_skips_logging() -> None:
    reporter = RunProgressReporter(
        task_name="demo",
        run_mode=BacktestMode.SLICE_BASED.value,
        enable_progress_display=False,
    )
    with patch(
        "core.modules.backtest_engine.core.shared.progress.logger.info"
    ) as info_mock:
        reporter.mark_phase(RunPhase.PREP)
        reporter.set_execute_total(2)
        reporter.mark_phase(RunPhase.EXECUTE)
        reporter.mark_execute_unit(1)

    info_mock.assert_not_called()


def test_report_execute_unit_from_context_invokes_hook() -> None:
    calls: list[int] = []

    def hook(completed: int) -> None:
        calls.append(completed)

    report_execute_unit_from_context(
        {"_engine_on_execute_unit_done": hook},
        3,
    )
    assert calls == [3]


def test_report_execute_unit_from_context_ignores_missing_hook() -> None:
    report_execute_unit_from_context({}, 1)
