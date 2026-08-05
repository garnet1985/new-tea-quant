"""Unit tests for SliceTaskState per-slice contract loading."""
from __future__ import annotations

from unittest.mock import patch

from core.modules.strategy.core.engines.enumerator.slice_based.executor import (
    SliceTaskState,
)


def _state_for_ensure() -> SliceTaskState:
    state = object.__new__(SliceTaskState)
    state.payload = {"entity_specified": [{"id": "a"}]}
    state.perf = None
    state._min_required = 5
    state._open_dates = [f"202401{i:02d}" for i in range(1, 31)]
    state._slice_index = 0
    state._window_load_sec = 0.0
    state._loaded_start_idx = -1
    state._loaded_end_idx = -1
    state._per_entity_load_count = 0
    state.entity_contracts = {}
    return state


def test_ensure_contracts_loads_with_lookback_and_counts() -> None:
    state = _state_for_ensure()
    with patch(
        "core.modules.strategy.core.services.entity_loader.job_bundle_loader.JobBundleLoader.load_per_entity_window",
        return_value={"k": object()},
    ) as load:
        # window starts at idx 10 → lookback start = 10 - 5 + 1 = 6
        state._ensure_contracts_for_window(10, 19)

    assert state._per_entity_load_count == 1
    assert state._loaded_start_idx == 6
    assert state._loaded_end_idx == 19
    load.assert_called_once()
    kwargs = load.call_args.kwargs
    assert kwargs["start"] == state._open_dates[6]
    assert kwargs["end"] == state._open_dates[19]

    # Covered range → no second IO
    with patch(
        "core.modules.strategy.core.services.entity_loader.job_bundle_loader.JobBundleLoader.load_per_entity_window",
    ) as load2:
        state._ensure_contracts_for_window(10, 19)
    load2.assert_not_called()
    assert state._per_entity_load_count == 1


def test_complete_formal_slice_forces_next_reload() -> None:
    state = _state_for_ensure()
    state._head_sample_slices = 0
    state._slice_samples = []
    state._window_start_idx = 0
    state._window_t0 = 0.0
    state._baseline_rss_mb = 0.0
    state._loaded_start_idx = 0
    state._loaded_end_idx = 19
    state.entity_contracts = {"k": object()}

    state._complete_formal_slice(19)
    assert state.entity_contracts == {}
    assert state._loaded_start_idx == -1

    with patch(
        "core.modules.strategy.core.services.entity_loader.job_bundle_loader.JobBundleLoader.load_per_entity_window",
        return_value={"k2": object()},
    ) as load:
        state._ensure_contracts_for_window(20, 29)
    assert load.call_count == 1
    assert state._per_entity_load_count == 1
