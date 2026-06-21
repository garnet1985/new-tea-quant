"""JobPipeline 子进程 execute：timeline batch / calendar_slice。"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Tuple

from core.infra.job_pipeline import JobContext
from core.modules.tag.enums import TagExecutionMode

logger = logging.getLogger(__name__)


def maybe_stage_in_worker(payload: Dict[str, Any]) -> Tuple[Dict[str, Any], float]:
    from core.modules.tag.engines.shared.staging.worker_runtime import (
        payload_needs_worker_stage,
        stage_payload_in_worker,
    )

    if not payload_needs_worker_stage(payload):
        return payload, 0.0
    stage_t0 = time.perf_counter()
    staged = stage_payload_in_worker(payload)
    return staged, time.perf_counter() - stage_t0


def run_worker_for_payload(job_payload: Dict[str, Any]) -> Dict[str, Any]:
    from core.modules.tag.services.discovery.worker_loader import import_tag_worker_class

    worker_module_path = job_payload.get("worker_module_path")
    worker_class_name = job_payload.get("worker_class_name")
    worker_file_path = str(job_payload.get("worker_file_path") or "")
    if not worker_module_path or not worker_class_name:
        raise ValueError(
            f"缺少 worker 模块信息: worker_module_path={worker_module_path}, "
            f"worker_class_name={worker_class_name}"
        )
    worker_class = import_tag_worker_class(
        worker_module_path=str(worker_module_path),
        worker_class_name=str(worker_class_name),
        worker_file_path=worker_file_path,
    )
    worker = worker_class(job_payload=job_payload)
    return worker.process_entity()


def entity_sub_payload(
    payload: Dict[str, Any],
    entity: Dict[str, Any],
    inject_slice: Dict[str, Any],
) -> Dict[str, Any]:
    keys = (
        "entity_type",
        "scenario_name",
        "update_mode",
        "tag_definitions",
        "settings",
        "worker_module_path",
        "worker_class_name",
        "worker_file_path",
        "global_extra_cache",
    )
    sub = {key: payload[key] for key in keys if key in payload}
    sub.update(entity)
    sub["_inject"] = inject_slice
    return sub


def execute_batch_entities(
    payload: Dict[str, Any],
    entities: List[Dict[str, Any]],
) -> Dict[str, Any]:
    exec_t0 = time.perf_counter()
    inject_root = payload.get("_inject") or {}
    by_entity = inject_root.get("by_entity") or {}
    all_tag_values: List[Dict[str, Any]] = []
    errors: List[str] = []
    ok = True

    for ent in entities:
        eid = str(ent.get("entity_id") or "")
        slice_inject = by_entity.get(eid)
        if slice_inject is None:
            ok = False
            errors.append(f"missing inject slice for entity_id={eid}")
            continue
        sub_payload = entity_sub_payload(payload, ent, slice_inject)
        try:
            result = run_worker_for_payload(sub_payload)
            if not result.get("success", True):
                ok = False
            all_tag_values.extend(result.get("tag_values") or [])
            errors.extend(result.get("errors") or [])
        except Exception as exc:
            ok = False
            msg = f"entity_id={eid}: {exc}"
            logger.exception("Batch job entity failed: %s", msg)
            errors.append(msg)

    return {
        "success": ok,
        "entity_count": len(entities),
        "tag_values": all_tag_values,
        "total_tags": len(all_tag_values),
        "errors": errors,
        "_profile_execute_sec": time.perf_counter() - exec_t0,
    }


def execute_tag_job(context: JobContext) -> Dict[str, Any]:
    """JobPipeline execute 回调（timeline + sliced）。"""
    payload = context.payload
    if payload.get("tag_execution_mode") == TagExecutionMode.CALENDAR_SLICE.value:
        from core.modules.tag.engines.sliced.worker import run_tag_calendar_slice_payload

        exec_t0 = time.perf_counter()
        try:
            out = run_tag_calendar_slice_payload(payload)
            out["_profile_execute_sec"] = time.perf_counter() - exec_t0
            return out
        except Exception as exc:
            logger.exception("Tag calendar_slice job failed: %s", exc)
            return {
                "success": False,
                "bulk": True,
                "tag_values": [],
                "error": str(exc),
                "_profile_execute_sec": time.perf_counter() - exec_t0,
            }

    stage_in_worker = bool(payload.get("_stage_in_worker"))
    try:
        payload, stage_sec = maybe_stage_in_worker(payload)
        entities = payload.get("entities")
        if isinstance(entities, list) and len(entities) > 1:
            out = execute_batch_entities(payload, entities)
            if stage_sec > 0:
                out["_profile_stage_sec"] = stage_sec
            return out

        exec_t0 = time.perf_counter()
        try:
            result = run_worker_for_payload(payload)
            execute_sec = time.perf_counter() - exec_t0
            out = {
                "success": bool(result.get("success", True)),
                "entity_id": payload.get("entity_id"),
                "tag_values": result.get("tag_values") or [],
                "total_tags": result.get("total_tags_created", 0),
                "processed_dates": result.get("processed_dates", 0),
                "total_dates": result.get("total_dates", 0),
                "errors": result.get("errors") or [],
                "_profile_execute_sec": execute_sec,
            }
            if stage_sec > 0:
                out["_profile_stage_sec"] = stage_sec
            return out
        except Exception as exc:
            logger.exception(
                "Job %s failed: %s", payload.get("entity_id", "unknown"), exc
            )
            out = {
                "success": False,
                "entity_id": payload.get("entity_id"),
                "tag_values": [],
                "error": str(exc),
                "_profile_execute_sec": time.perf_counter() - exec_t0,
            }
            if stage_sec > 0:
                out["_profile_stage_sec"] = stage_sec
            return out
    finally:
        if stage_in_worker:
            from core.modules.tag.engines.shared.staging.worker_runtime import (
                release_worker_runtime,
            )

            release_worker_runtime()
