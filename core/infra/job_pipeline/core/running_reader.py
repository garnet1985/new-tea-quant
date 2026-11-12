"""读 running 快照（自管 registry）。"""

from __future__ import annotations

from typing import Any, Dict, Optional

from core.infra.job_pipeline.core import registry_store


def read_running_job() -> Optional[Dict[str, Any]]:
    """当前 running 任务；没有则 ``None``。"""
    return registry_store.read_running()
