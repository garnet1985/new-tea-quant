def test_calendar_slice_runtime_settings_defaults():
    from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.runtime.settings import (
        CalendarSliceRuntimeSettings,
    )

    rt = CalendarSliceRuntimeSettings.from_worker_config()
    assert rt.prefetch_enabled is True
    assert rt.reader_workers == 8


def test_calendar_slice_runtime_settings_explicit():
    from unittest.mock import patch

    from core.modules.backtest_engine.core.slice_based.config import SliceConfig
    from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.runtime.settings import (
        CalendarSliceRuntimeSettings,
    )

    with patch.object(
        SliceConfig,
        "resolve_dispatch_performance",
        return_value={"reader_workers": 2, "queue_depth": 2, "prefetch_enabled": True},
    ):
        rt = CalendarSliceRuntimeSettings.from_worker_config()
    assert rt.reader_workers == 2
    assert rt.queue_depth == 2


def test_calendar_slice_runtime_settings_prefetch_off_forces_single_reader():
    from unittest.mock import patch

    from core.modules.backtest_engine.core.slice_based.config import SliceConfig
    from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.runtime.settings import (
        CalendarSliceRuntimeSettings,
    )

    with patch.object(
        SliceConfig,
        "resolve_dispatch_performance",
        return_value={
            "queue_depth": 2,
            "prefetch_enabled": False,
            "reader_workers": 4,
        },
    ):
        rt = CalendarSliceRuntimeSettings.from_worker_config()
    assert rt.prefetch_enabled is False
    assert rt.queue_depth == 1
    assert rt.reader_workers == 1
