"""标签计算的进度文件只记完成数。说明和结果仍在原来的任务文件。"""

from __future__ import annotations

import pytest

from core.modules.strategy.core.services.progress.progress_recorder import ProgressRecorder
from core.modules.tag.core.services.progress import TagRunProgress

pytestmark = pytest.mark.force_run


@pytest.fixture
def progress_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("NTQ_PROGRESS_DIR", str(tmp_path / "shared"))
    monkeypatch.setenv("NTQ_PROGRESS_FLUSH_DELAY", "0")

    def _build(channel, file_key):
        return tmp_path / "jobs" / channel / f"{file_key}.json"

    monkeypatch.setattr(ProgressRecorder, "build_path", staticmethod(_build))
    from core.infra.progress.core import store

    store.reset()
    yield tmp_path
    store.reset()


def test_tag_run_publishes_job_counts(progress_dir):
    from core.infra.progress import Progress

    prog = TagRunProgress.for_job("macro/rate", "job1")
    prog.seed()
    prog.mark_running()
    prog.tick_from_pipeline({"finished": 2, "total_jobs": 8, "progress_pct": 10})

    body = TagRunProgress.get_poll_dto(tag_key="macro/rate", job_id="job1")
    assert body["status"] == "running"
    assert body["progress"] == 25.0
    assert body["label"] == "执行计算 2/8"

    shared = Progress.read("tag-macro-rate-job1")
    assert shared["job"] == "tag"
    assert shared["source"] == "macro/rate"
    assert shared["done"] == 2
    assert shared["total"] == 8
    assert shared["detail"] == "执行计算 2/8"
    assert "is_success" not in shared

    prog.complete()
    done = TagRunProgress.get_poll_dto(tag_key="macro/rate", job_id="job1")
    assert done["status"] == "completed"
    assert done["progress"] == 100.0
    assert done["is_success"] is True
    assert Progress.read("tag-macro-rate-job1")["status"] == "completed"


def test_tag_run_failure_marks_the_progress_file(progress_dir):
    from core.infra.progress import Progress

    prog = TagRunProgress.for_job("macro/rate", "job2")
    prog.seed()
    prog.fail("场景缺失")
    body = TagRunProgress.get_poll_dto(tag_key="macro/rate", job_id="job2")
    assert body["status"] == "failed"
    assert body["reason"] == "场景缺失"
    assert Progress.read("tag-macro-rate-job2")["status"] == "failed"
    assert Progress.read("tag-macro-rate-job2")["detail"] == "场景缺失"
