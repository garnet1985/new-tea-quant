"""跨模块契约：任务状态、种类常量（随实现扩展）。

推荐::

    from core.infra.job_pipeline import JobPipeline
    from core.infra.job_pipeline.contracts import JobStatus
"""

from __future__ import annotations

# 与现行 TaskGuard kinds 对齐，便于绞杀期映射；并行扩容时再拆锁粒度。
VALID_KINDS = frozenset(
    {
        "tag_run",
        "strategy_scan",
        "strategy_run",
        "strategy_attribute",
        "strategy_rolling",
        "data_renew",
    }
)


class JobStatus:
    """任务生命周期状态名（字符串常量，落盘与 API 同形）。"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    STALE = "stale"
