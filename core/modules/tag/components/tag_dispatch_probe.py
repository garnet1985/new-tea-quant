"""Tag 调度探针：子进程试跑与生产相同的 stage+算路径。"""
from __future__ import annotations

from typing import Any, Dict, Optional

from core.infra.worker.dispatch_probe import (
    DEFAULT_PROBE_ENTITIES,
    DEFAULT_PROBE_SAFETY_FACTOR,
    PROBE_EXECUTOR_TAG,
    DispatchProbeResult,
    run_dispatch_probe_in_subprocess,
    should_run_dispatch_probe,
)

__all__ = [
    "DEFAULT_PROBE_ENTITIES",
    "DEFAULT_PROBE_SAFETY_FACTOR",
    "DispatchProbeResult",
    "TagDispatchProbeResult",
    "execute_tag_probe_payload",
    "run_tag_dispatch_probe",
    "should_run_dispatch_probe",
]

TagDispatchProbeResult = DispatchProbeResult


def execute_tag_probe_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    from core.infra.job_pipeline.types import JobContext
    from core.modules.tag.components.job_staging.worker_runtime import release_worker_runtime
    from core.modules.tag.tag_manager import TagManager

    payload = dict(payload)
    payload["_stage_in_worker"] = True
    payload["_dispatch_probe"] = True
    ctx = JobContext(
        job_id=str(payload.get("_job_id") or "tag_probe"),
        payload=payload,
        run_name=str(payload.get("_run_name") or "tag:probe"),
    )
    try:
        out = TagManager._execute_single_job(ctx)
        if not isinstance(out, dict):
            return {"success": True, "data": out}
        return out
    finally:
        if payload.get("_stage_in_worker"):
            release_worker_runtime()


def run_tag_dispatch_probe(
    probe_job_payload: Dict[str, Any],
    *,
    performance: Optional[Dict[str, Any]] = None,
) -> DispatchProbeResult:
    payload = dict(probe_job_payload)
    entities = payload.get("entities")
    n_entities = (
        len(entities)
        if isinstance(entities, list) and entities
        else (1 if payload.get("entity_id") else 0)
    )
    payload["_probe_entity_count"] = max(1, n_entities)

    return run_dispatch_probe_in_subprocess(
        payload,
        executor=PROBE_EXECUTOR_TAG,
        performance=performance,
        log_label="Tag",
    )
