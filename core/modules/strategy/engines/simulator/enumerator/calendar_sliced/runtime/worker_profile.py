"""Strategy enum calendar_slice：从 worker.json 读取 enumerator 段。"""
from __future__ import annotations

from typing import Any, Dict

from core.infra.project_context import ProjectContext


def _load_enumerator_section(section: str) -> Dict[str, Any]:
    cfg = ProjectContext.config.load_core_config("worker")
    job_pipeline = cfg.get("job_pipeline") or {}
    if not isinstance(job_pipeline, dict):
        job_pipeline = {}

    merged: Dict[str, Any] = {}
    for block_name in ("default", "enumerator"):
        block = job_pipeline.get(block_name)
        if not isinstance(block, dict):
            continue
        for field in ("reserve_cores", "max_parallel_jobs_cap"):
            if field in block:
                merged[field] = block[field]

    enum_block = job_pipeline.get("enumerator")
    if isinstance(enum_block, dict):
        section_block = enum_block.get(section)
        if isinstance(section_block, dict):
            merged.update(section_block)
    return merged


def profile_enumerator_dispatch_config() -> Dict[str, Any]:
    """``worker.json`` → ``job_pipeline.enumerator.dispatch``。"""
    cfg = dict(_load_enumerator_section("dispatch"))
    cfg.setdefault("memory_budget_mb", "auto")
    cfg.setdefault("dispatch_memory_budget_mb", "auto")
    return cfg


def profile_enumerator_calendar_slice_config() -> Dict[str, Any]:
    """``worker.json`` → ``job_pipeline.enumerator.calendar_slice``。"""
    cfg = dict(_load_enumerator_section("calendar_slice"))
    cfg.setdefault("reader_workers", "auto")
    cfg.setdefault("queue_depth", "auto")
    cfg.setdefault("prefetch_enabled", True)
    return cfg
