"""DataSourcePipelineRunner 多 bundle 调度（mock fetch）。"""
from unittest.mock import Mock

import pandas as pd

from core.modules.data_source.core.data_class.api_job import ApiJob
from core.modules.data_source.core.data_class.api_job_bundle import ApiJobBundle
from core.modules.data_source.core.service.pipeline.runner import DataSourcePipelineRunner
from core.modules.data_source.core.service.pipeline.save_memory_budget import SaveMemoryBudget


def _context(*, retain: bool = False, budget_bytes: int = 1):
    saved = []

    def to_frames(_ctx, _bundle, result):
        rows = []
        for value in result.values():
            if isinstance(value, list):
                rows.extend(value)
        if not rows:
            return []
        return [pd.DataFrame(rows)]

    def save_frames(_ctx, frames):
        saved.append(frames)

    return {
        "data_source_key": "test_ds",
        "config": Mock(),
        "providers": {},
        "data_manager": Mock(db=Mock(config={"database_type": "mysql"})),
        "retain_results": retain,
        "_save_budget": SaveMemoryBudget(budget_bytes=budget_bytes, cpu_cap=2, write_reserve_bytes=0),
        "_bundle_to_frames": to_frames,
        "_save_frames": save_frames,
        "_saved": saved,
    }


def _patch_execute(mod, payload):
    original = mod.ApiJobExecutor.execute

    async def patched(_self, api_jobs):
        return payload(api_jobs)

    mod.ApiJobExecutor.execute = patched
    return original


def test_run_bundles_flushes_frames_and_drops_merged_results():
    import core.modules.data_source.core.service.api_job_executor as mod

    job_a = ApiJob(job_id="a", provider_name="p", method="m", api_name="a")
    bundles = [
        ApiJobBundle(bundle_id=f"b{i}", apis=[job_a])
        for i in range(3)
    ]
    context = _context(budget_bytes=1)
    original = _patch_execute(mod, lambda api_jobs: {api_jobs[0].job_id: [{"x": 1}]})
    try:
        merged = DataSourcePipelineRunner().run_bundles(
            context,
            bundles,
            enrich_result_for_batch=lambda _ctx, _b, result: result,
        )
    finally:
        mod.ApiJobExecutor.execute = original

    assert merged == {}
    assert sum(len(batch) for batch in context["_saved"]) == 3


def test_run_bundles_dependency_source_keeps_results():
    import core.modules.data_source.core.service.api_job_executor as mod

    job_a = ApiJob(job_id="a", provider_name="p", method="m", api_name="a")
    bundle = ApiJobBundle(bundle_id="b1", apis=[job_a])
    context = _context(retain=True, budget_bytes=10**9)
    original = _patch_execute(mod, lambda api_jobs: {api_jobs[0].job_id: [{"x": 1}]})
    try:
        merged = DataSourcePipelineRunner().run_bundles(
            context,
            [bundle],
            enrich_result_for_batch=lambda _ctx, _b, result: result,
        )
    finally:
        mod.ApiJobExecutor.execute = original

    assert merged
    assert context["_saved"]
