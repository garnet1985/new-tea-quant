from unittest.mock import patch

from core.infra.job_pipeline.worker_profile import (
    WorkerProfiles,
    profile_reserve_cores,
    resolve_worker_profile,
)


def test_worker_profile_merges_default_and_specific():
    block = {
        "default": {"reserve_cores": 1, "max_parallel_jobs_cap": None},
        "enumerator": {"reserve_cores": 2},
    }
    with patch(
        "core.infra.job_pipeline.worker_profile._job_pipeline_block",
        return_value=block,
    ):
        prof = resolve_worker_profile(WorkerProfiles.ENUMERATOR)
    assert prof["reserve_cores"] == 2
    assert prof["max_parallel_jobs_cap"] is None


def test_unknown_profile_falls_back_to_default():
    block = {"default": {"reserve_cores": 3}}
    with patch(
        "core.infra.job_pipeline.worker_profile._job_pipeline_block",
        return_value=block,
    ):
        assert profile_reserve_cores("unknown_worker") == 3
