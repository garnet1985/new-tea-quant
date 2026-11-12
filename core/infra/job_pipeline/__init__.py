"""
长任务执行管道（``infra.job_pipeline``）。

包根仅导出 ``JobPipeline``；类型见 ``contracts``。
设计见 ``docs/DECISIONS.md``。
"""

from .job_pipeline import JobPipeline

__all__ = ["JobPipeline"]
