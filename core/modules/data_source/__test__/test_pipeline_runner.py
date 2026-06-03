"""DataSourcePipelineRunner 多 bundle 调度（mock fetch）。"""
from unittest.mock import Mock

import pytest

from core.modules.data_source.data_class.api_job import ApiJob
from core.modules.data_source.data_class.api_job_bundle import ApiJobBundle
from core.modules.data_source.service.pipeline.runner import DataSourcePipelineRunner


@pytest.fixture
def mock_config_batch():
    cfg = Mock()
    cfg.get_save_mode.return_value = "batch"
    cfg.is_save_batch_size_auto.return_value = False
    cfg.get_save_batch_size.return_value = 2
    return cfg


def test_run_bundles_batch_save_flushes_via_on_result(mock_config_batch):
    saved_batches = []
    saved_single = []

    def on_batch(ctx, items):
        saved_batches.append(list(items))

    def on_single(ctx, bundle, result):
        saved_single.append((bundle, result))

    job_a = ApiJob(job_id="a", provider_name="p", method="m", api_name="a")
    job_b = ApiJob(job_id="b", provider_name="p", method="m", api_name="b")
    bundle1 = ApiJobBundle(bundle_id="b1", apis=[job_a])
    bundle2 = ApiJobBundle(bundle_id="b2", apis=[job_b])
    bundle3 = ApiJobBundle(bundle_id="b3", apis=[job_a])

    context = {
        "data_source_key": "test_ds",
        "config": mock_config_batch,
        "providers": {},
        "data_manager": Mock(db=Mock(config={"database_type": "duckdb"})),
    }

    async def fake_execute(api_jobs):
        return {api_jobs[0].job_id: [{"x": 1}]}

    import core.modules.data_source.service.api_job_executor as mod

    original = mod.ApiJobExecutor.execute

    async def patched(self, api_jobs):
        return await fake_execute(api_jobs)

    mod.ApiJobExecutor.execute = patched
    try:
        runner = DataSourcePipelineRunner()
        merged = runner.run_bundles(
            context,
            [
                ("b1", [job_a], bundle1),
                ("b2", [job_b], bundle2),
                ("b3", [job_a], bundle3),
            ],
            on_after_single_bundle_complete=on_single,
            on_after_batch_bundles_complete=on_batch,
            enrich_result_for_batch=lambda _ctx, _b, r: r,
        )
    finally:
        mod.ApiJobExecutor.execute = original

    assert merged
    assert len(saved_batches) >= 1
    assert sum(len(b) for b in saved_batches) == 3
    assert not saved_single
