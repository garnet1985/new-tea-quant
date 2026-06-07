"""JobPipeline 编排：settings、hooks、runner。"""
from core.infra.job_pipeline.pipeline.hooks import ExecuteFn, OnReleaseHook, OnResultHook
from core.infra.job_pipeline.pipeline.runner import JobPipeline
from core.infra.job_pipeline.pipeline.settings import JobPipelineSettings

__all__ = [
    "ExecuteFn",
    "JobPipeline",
    "JobPipelineSettings",
    "OnReleaseHook",
    "OnResultHook",
]
