"""跨模块契约：任务状态、种类常量（随实现扩展）。

推荐::

    from core.infra.job_pipeline import JobPipeline
    from core.infra.job_pipeline.contracts import JobStatus, JobRunningBusyError, VALID_KINDS
"""

from __future__ import annotations

from typing import Any, Dict, Optional

# 长任务 kind；并行扩容时再拆锁粒度。
# 注意：``strategy_scan`` 已可占 running 槽（agent），但 BFF 扫描仍用独立单飞线程，
# 尚未 ``register_handler`` / 入队（见 DECISIONS DEC-07）。
VALID_KINDS = frozenset(
    {
        "tag_run",
        "strategy_scan",
        "strategy_run",
        "strategy_attribute",
        "strategy_rolling",
        "data_renew",
        "import_data",
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


class JobRunningBusyError(RuntimeError):
    """全局 running 槽已被占用。"""

    def __init__(self, existing: Optional[Dict[str, Any]] = None) -> None:
        self.existing = existing if isinstance(existing, dict) else {}
        kind = self.existing.get("kind") or "unknown"
        jid = self.existing.get("job_id") or ""
        super().__init__(f"系统任务进行中（{kind}）" + (f" job_id={jid}" if jid else ""))


__all__ = [
    "VALID_KINDS",
    "JobStatus",
    "JobRunningBusyError",
]
