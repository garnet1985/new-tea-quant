"""TagPipelineHooks 进度分母应跟 BE RunProgress（batch），而不是 len(jobs)。"""

from __future__ import annotations

import pytest

from core.modules.backtest_engine.contracts import JobReport, RunProgress
from core.modules.tag.core.engines.per_entity.shared.pipeline_hooks import (
    TagPipelineHooks,
    TagPipelineRunContext,
)

pytestmark = pytest.mark.force_run


@pytest.fixture
def progress_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("NTQ_PROGRESS_DIR", str(tmp_path / "shared"))
    monkeypatch.setenv("NTQ_PROGRESS_FLUSH_DELAY", "0")
    from core.infra.progress.core import store

    store.reset()
    yield tmp_path
    store.reset()


class _Flush:
    def extend(self, rows):
        return len(rows or [])


def test_emit_progress_uses_run_progress_batch_total():
    snapshots = []

    def on_progress(snap):
        snapshots.append(dict(snap))

    ctx = TagPipelineRunContext(
        flush=_Flush(),
        total_jobs=1,  # entity_based 常见：一个 BacktestJob
        on_progress=on_progress,
    )
    TagPipelineHooks.bind(ctx)
    try:
        TagPipelineHooks.on_receive_task_result(
            JobReport(job_id="b1", success=True, data={"tag_values": []}),
            RunProgress(finished=1, total=20, ok=1, fail=0),
        )
        TagPipelineHooks.on_receive_task_result(
            JobReport(job_id="b2", success=True, data={"tag_values": []}),
            RunProgress(finished=5, total=20, ok=5, fail=0),
        )
    finally:
        TagPipelineHooks.clear()

    assert snapshots[0]["finished"] == 1
    assert snapshots[0]["total"] == 20
    assert snapshots[1]["finished"] == 5
    assert snapshots[1]["total"] == 20


def test_seed_publish_does_not_invent_denominator_one(progress_dir):
    from core.infra.progress import Progress
    from core.modules.tag.core.services.progress import TagRunProgress

    prog = TagRunProgress.for_job("demo/market_cap_tier", "job-x")
    prog.seed()
    snap = Progress.read("tag-demo-market_cap_tier-job-x")
    assert snap is not None
    assert int(snap.get("total") or 0) == 0
    assert float(snap.get("ratio") or 0) == 0.0
