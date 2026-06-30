"""Strategy execution：从 worker.json 读取 dispatch / calendar_slice 段。"""
from __future__ import annotations

from typing import Any, Dict

from core.infra.project_context import ProjectContext


def _load_profile_section(profile: str, section: str) -> Dict[str, Any]:
    cfg = ProjectContext.config.load_core_config("worker")
    job_pipeline = cfg.get("job_pipeline") or {}
    if not isinstance(job_pipeline, dict):
        job_pipeline = {}

    merged: Dict[str, Any] = {}
    for block_name in ("default", profile):
        block = job_pipeline.get(block_name)
        if not isinstance(block, dict):
            continue
        for field in ("reserve_cores", "max_parallel_jobs_cap"):
            if field in block:
                merged[field] = block[field]

    profile_block = job_pipeline.get(profile)
    if isinstance(profile_block, dict):
        section_block = profile_block.get(section)
        if isinstance(section_block, dict):
            merged.update(section_block)
    return merged


def profile_price_factor_dispatch_config() -> Dict[str, Any]:
    """``worker.json`` → ``job_pipeline.price_factor.dispatch``。"""
    cfg = dict(_load_profile_section("price_factor", "dispatch"))
    cfg.setdefault("entities_per_job", 1000)
    cfg.setdefault("dispatch_probe", False)
    cfg.setdefault("force_main_process", False)
    return cfg


def profile_scanner_dispatch_config() -> Dict[str, Any]:
    """``worker.json`` → ``job_pipeline.scanner.dispatch``。"""
    cfg = dict(_load_profile_section("scanner", "dispatch"))
    cfg.setdefault("entities_per_job", 1)
    cfg.setdefault("dispatch_probe", False)
    return cfg


__all__ = [
    "profile_price_factor_dispatch_config",
    "profile_scanner_dispatch_config",
]
