"""
MIGRATED → ``core.modules.tag.core.engines.slice_based``

旧 calendar_slice（opaque orchestrator + BaseTagWorker）。
新路径::

    from core.modules.tag.core.engines.slice_based import (
        TagSliceJobBuilder,
        TagSliceJobExecutor,
    )

AUDIT: 待 TagManager / tag_job_pipeline 切走后删除本包。
"""
