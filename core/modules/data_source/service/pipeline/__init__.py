"""Data source JobPipeline 集成（线程后端 + on_result 攒批写库）。"""

from core.modules.data_source.service.pipeline.runner import (
    DataSourcePipelineRunner,
    normalize_job_bundles,
)

__all__ = [
    "DataSourcePipelineRunner",
    "normalize_job_bundles",
]
