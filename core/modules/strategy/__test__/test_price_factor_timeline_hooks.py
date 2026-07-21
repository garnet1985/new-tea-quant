"""price_factor JobExecutor：RunCallbacks 钩子面（含 on_tick）。"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from core.modules.backtest_engine.contracts import RunCallbacks
from core.modules.strategy.core.engines.price_factor.executor import JobExecutor

pytestmark = pytest.mark.force_run


def test_build_run_callbacks_wires_lifecycle_and_on_tick() -> None:
    callbacks = JobExecutor.build_run_callbacks()
    assert isinstance(callbacks, RunCallbacks)
    assert callbacks.on_before_task_start is not None
    assert callbacks.on_tick is not None
    assert callbacks.on_after_all_tasks_complete is not None
    assert callbacks.on_before_task_start.__func__ is JobExecutor.on_before_task_start.__func__
    assert callbacks.on_tick.__func__ is JobExecutor.on_tick.__func__


def test_on_tick_is_noop_for_now() -> None:
    ctx = SimpleNamespace(job_id="batch_0", payload={}, init={})
    JobExecutor.on_tick(ctx, "20240102", 0)
