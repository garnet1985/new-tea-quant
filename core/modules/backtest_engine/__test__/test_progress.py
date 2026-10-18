"""RunProgressReporter phased progress tests."""
from __future__ import annotations

from unittest.mock import patch

from core.modules.backtest_engine.core.shared.modes import BacktestMode
from core.modules.backtest_engine.core.shared.progress import (
    RunPhase,
    RunProgressReporter,
    _PHASE_WEIGHTS,
    attach_round,
    phase_steps,
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
    weight_total = sum(_PHASE_WEIGHTS.values())
    assert plan.percent == 100 * _PHASE_WEIGHTS[RunPhase.PREP] / weight_total

    reporter.set_execute_total(10)
    reporter.mark_phase(RunPhase.EXECUTE)
    execute_mid = reporter.mark_execute_unit(5)
    covered = (
        _PHASE_WEIGHTS[RunPhase.PREP]
        + _PHASE_WEIGHTS[RunPhase.PLAN]
        + _PHASE_WEIGHTS[RunPhase.EXECUTE] * 0.5
    )
    assert execute_mid.percent == 100 * covered / weight_total

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


def test_attached_round_counts_toward_the_campaign(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("NTQ_PROGRESS_DIR", str(tmp_path / "shared"))
    monkeypatch.setenv("NTQ_PROGRESS_FLUSH_DELAY", "0")
    from core.infra.progress import Progress
    from core.infra.progress.core import store

    store.reset()
    root = "attribute-demo-enumerate"
    steps = []
    for index in (1, 2):
        round_id = f"{root}:r{index}"
        steps.append(
            {
                "id": round_id,
                "label": f"第 {index} 轮",
                "weight": 1,
                "steps": phase_steps(round_id),
            }
        )
    Progress.start(root, job="attribute", label="归因", steps=steps)

    with attach_round(root, f"{root}:r1", index=1, total=2):
        reporter = RunProgressReporter(
            task_name="strategy_demo",
            run_mode=BacktestMode.ENTITY_BASED.value,
            enable_progress_display=False,
        )
        reporter.mark_phase(RunPhase.FINISH)
    Progress.finish(f"{root}:r1")
    assert Progress.read(root)["ratio"] == 0.5

    with attach_round(root, f"{root}:r2", index=2, total=2):
        reporter = RunProgressReporter(
            task_name="strategy_demo",
            run_mode=BacktestMode.ENTITY_BASED.value,
            enable_progress_display=False,
        )
        reporter.mark_phase(RunPhase.PLAN)
        weight_total = sum(_PHASE_WEIGHTS.values())
        expected = (1 + _PHASE_WEIGHTS[RunPhase.PREP] / weight_total) / 2
        assert reporter.percent == expected * 100
    store.reset()
