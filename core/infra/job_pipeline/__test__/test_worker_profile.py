from unittest.mock import patch

from core.infra.job_pipeline.profile import (
    WorkerProfiles,
    profile_dispatch_config,
    profile_reserve_cores,
    resolve_worker_profile,
)


def test_worker_profile_merges_default_and_specific():
    block = {
        "default": {"reserve_cores": 1, "max_parallel_jobs_cap": None},
        "enumerator": {"reserve_cores": 2},
    }
    with patch(
        "core.infra.job_pipeline.profile.resolver._job_pipeline_block",
        return_value=block,
    ):
        prof = resolve_worker_profile(WorkerProfiles.ENUMERATOR)
    assert prof["reserve_cores"] == 2
    assert prof["max_parallel_jobs_cap"] is None


def test_unknown_profile_falls_back_to_default():
    block = {"default": {"reserve_cores": 3}}
    with patch(
        "core.infra.job_pipeline.profile.resolver._job_pipeline_block",
        return_value=block,
    ):
        assert profile_reserve_cores("unknown_worker") == 3


def test_profile_dispatch_merges_defaults():
    block = {
        "price_factor": {
            "dispatch": {"entities_per_job": 500},
        }
    }
    with patch(
        "core.infra.job_pipeline.profile.resolver._job_pipeline_block",
        return_value=block,
    ):
        cfg = profile_dispatch_config(WorkerProfiles.PRICE_FACTOR)
    assert cfg["entities_per_job"] == 500
    assert cfg["dispatch_probe"] is False


def test_profile_dispatch_merges_enumerator_defaults():
    block = {
        "enumerator": {
            "dispatch": {"entities_per_job": 80},
        }
    }
    with patch(
        "core.infra.job_pipeline.profile.resolver._job_pipeline_block",
        return_value=block,
    ):
        cfg = profile_dispatch_config(WorkerProfiles.ENUMERATOR)
    assert cfg["entities_per_job"] == 80
    assert cfg["dispatch_probe"] is True
