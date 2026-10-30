"""JobPipeline：定型前只保留最小导入烟测。"""

from __future__ import annotations

from core.infra.job_pipeline import JobPipeline


def test_facade_importable() -> None:
    assert JobPipeline is not None
    assert callable(JobPipeline.get_running_job)
