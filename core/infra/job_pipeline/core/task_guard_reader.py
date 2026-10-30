"""绞杀期只读适配：从 TaskGuard 租约拼装管道任务快照。

进度百分比仍由各业务 Progress 持有；本层不依赖 ``modules.*``，避免 infra→业务倒置。
BFF / FED 可用 ``job_id`` + ``kind`` + ``resource_key`` 再去拉细进度。
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from core.infra.job_pipeline.contracts import JobStatus
from core.infra.task_guard import TaskGuard


def read_running_job() -> Optional[Dict[str, Any]]:
    """若 TaskGuard 显示忙且租约有效，返回统一任务快照；否则 ``None``。"""
    status = TaskGuard.read_status()
    if not isinstance(status, dict) or not status.get("busy"):
        return None
    job_id = str(status.get("job_id") or "").strip()
    if not job_id:
        return None
    kind = str(status.get("kind") or "").strip() or None
    resource_key = str(status.get("resource_key") or "").strip()
    label = str(status.get("label") or "").strip()
    domains = status.get("domains")
    if not isinstance(domains, list):
        domains = []
    return {
        "job_id": job_id,
        "kind": kind,
        "resource_key": resource_key,
        "label": label or resource_key or (kind or ""),
        "status": JobStatus.RUNNING,
        "domains": [str(d) for d in domains],
        "started_at": status.get("started_at"),
        "progress": None,
    }
