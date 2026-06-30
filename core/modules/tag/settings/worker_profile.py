"""Tag 模块：从 worker.json 读取 job_pipeline.tag 段（不依赖 backtest_engine / job_pipeline）。"""
from __future__ import annotations

from typing import Any, Dict

from core.infra.project_context import ProjectContext


def _load_tag_section(section: str) -> Dict[str, Any]:
    cfg = ProjectContext.config.load_core_config("worker")
    job_pipeline = cfg.get("job_pipeline") or {}
    if not isinstance(job_pipeline, dict):
        job_pipeline = {}

    merged: Dict[str, Any] = {}
    for block_name in ("default", "tag"):
        block = job_pipeline.get(block_name)
        if not isinstance(block, dict):
            continue
        for field in ("reserve_cores", "max_parallel_jobs_cap"):
            if field in block:
                merged[field] = block[field]

    tag_block = job_pipeline.get("tag")
    if isinstance(tag_block, dict):
        section_block = tag_block.get(section)
        if isinstance(section_block, dict):
            merged.update(section_block)
    return merged


def profile_tag_entity_timeline_config() -> Dict[str, Any]:
    """``worker.json`` → ``job_pipeline.tag.entity_timeline`` 默认值。"""
    cfg = dict(_load_tag_section("entity_timeline"))
    cfg.setdefault("entities_per_job", "auto")
    cfg.setdefault("dispatch_probe", True)
    cfg.setdefault("stage_in_worker", True)
    cfg.setdefault("memory_floor_mb", "auto")
    return cfg


def profile_tag_calendar_slice_config() -> Dict[str, Any]:
    """``worker.json`` → ``job_pipeline.tag.calendar_slice`` 默认值。"""
    return dict(_load_tag_section("calendar_slice"))
