def test_calendar_slice_runtime_settings_defaults():
    from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.runtime.settings import (
        CalendarSliceRuntimeSettings,
    )

    rt = CalendarSliceRuntimeSettings.from_worker_profile()
    assert rt.prefetch_enabled is True
    assert rt.reader_workers == 8  # auto default upper bound placeholder


def test_calendar_slice_runtime_settings_explicit():
    from unittest.mock import patch

    from core.infra.job_pipeline.profile import WorkerProfiles
    from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.runtime.settings import (
        CalendarSliceRuntimeSettings,
    )

    block = {
        "enumerator": {
            "calendar_slice": {"reader_workers": 2, "queue_depth": 2},
        }
    }
    with patch(
        "core.infra.job_pipeline.profile.resolver._job_pipeline_block",
        return_value=block,
    ):
        rt = CalendarSliceRuntimeSettings.from_worker_profile(WorkerProfiles.ENUMERATOR)
    assert rt.reader_workers == 2
    assert rt.queue_depth == 2


def test_calendar_slice_runtime_settings_prefetch_off_forces_single_reader():
    from unittest.mock import patch

    from core.infra.job_pipeline.profile import WorkerProfiles
    from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.runtime.settings import (
        CalendarSliceRuntimeSettings,
    )

    block = {
        "enumerator": {
            "calendar_slice": {
                "queue_depth": 2,
                "prefetch_enabled": False,
                "reader_workers": 4,
            },
        }
    }
    with patch(
        "core.infra.job_pipeline.profile.resolver._job_pipeline_block",
        return_value=block,
    ):
        rt = CalendarSliceRuntimeSettings.from_worker_profile(WorkerProfiles.ENUMERATOR)
    assert rt.prefetch_enabled is False
    assert rt.queue_depth == 1
    assert rt.reader_workers == 1
