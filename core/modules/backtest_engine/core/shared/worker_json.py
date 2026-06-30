"""BacktestEngine 内部：从 worker.json job_pipeline 段读取 dispatch 配置。"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from core.infra.project_context import ProjectContext


def load_job_pipeline_section(profile_name: str, section_name: str) -> Dict[str, Any]:
    """合并 default + profile 的 reserve 字段与 profile.section。"""
    cfg = ProjectContext.config.load_core_config("worker")
    job_pipeline = cfg.get("job_pipeline") or {}
    if not isinstance(job_pipeline, dict):
        job_pipeline = {}

    performance: Dict[str, Any] = {}
    for block_name in ("default", profile_name):
        block = job_pipeline.get(block_name)
        if not isinstance(block, dict):
            continue
        for field in ("reserve_cores", "max_parallel_jobs_cap"):
            if field in block:
                performance[field] = block[field]

    profile_block = job_pipeline.get(profile_name)
    if isinstance(profile_block, dict):
        section = profile_block.get(section_name)
        if isinstance(section, dict):
            performance.update(section)
    return performance


def resolve_executor_section(
    executor_key: str,
    mapping: Dict[str, Tuple[str, str]],
    *,
    defaults: Optional[Dict[str, Any]] = None,
    setdefaults: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    key = str(executor_key or "").strip()
    entry = mapping.get(key)
    if entry is None:
        raise ValueError(
            f"unknown executor_key: {key!r}; supported: {sorted(mapping)}"
        )
    profile_name, section_name = entry
    performance = load_job_pipeline_section(profile_name, section_name)
    if defaults:
        performance = {**defaults, **performance}
    if setdefaults:
        for field, value in setdefaults.items():
            performance.setdefault(field, value)
    return performance
