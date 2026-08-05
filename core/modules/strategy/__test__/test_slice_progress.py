"""SliceTaskState reports execute-unit progress on formal slice boundaries."""
from __future__ import annotations

import time

from core.modules.strategy.core.engines.enumerator.slice_based.executor import (
    SliceTaskState,
)


def _bare_state(*, head_sample_slices: int = 2) -> SliceTaskState:
    state = object.__new__(SliceTaskState)
    state.payload = {}
    state._head_sample_slices = head_sample_slices
    state._slice_samples = []
    state._slice_index = 0
    state._window_start_idx = 0
    state._window_t0 = time.perf_counter()
    state._window_load_sec = 0.05
    state._window_compute_t0 = state._window_t0
    state._baseline_rss_mb = 0.0
    state._slice_open_days = 20
    state._loaded_start_idx = 0
    state._loaded_end_idx = 19
    state.entity_contracts = {"k": object()}
    state._per_entity_load_count = 1
    state._open_dates = []
    return state


def test_complete_formal_slice_invokes_progress_hook() -> None:
    calls: list[int] = []
    state = _bare_state(head_sample_slices=2)
    state.payload["_engine_on_execute_unit_done"] = calls.append

    state._complete_formal_slice(19)
    state._complete_formal_slice(39)
    state._complete_formal_slice(59)

    assert calls == [1, 2, 3]
    assert state._slice_index == 3
    assert len(state._slice_samples) == 2  # only first N head samples
    assert state._window_start_idx == 60
    assert state._slice_samples[0]["load_sec"] == 0.05
    assert state.entity_contracts == {}
    assert state._loaded_start_idx == -1


def test_complete_formal_slice_without_hook_is_noop_progress() -> None:
    state = _bare_state(head_sample_slices=0)
    state._complete_formal_slice(19)
    assert state._slice_index == 1
    assert state._slice_samples == []
