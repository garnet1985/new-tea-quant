"""Strategy enum calendar_slice dispatch（读取 strategy/settings/dispatch.yaml）。"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml

_DISPATCH_PATH = Path(__file__).resolve().parents[5] / "settings" / "dispatch.yaml"


def _load_dispatch_root() -> Dict[str, Any]:
    if not _DISPATCH_PATH.is_file():
        raise FileNotFoundError(f"strategy dispatch config not found: {_DISPATCH_PATH}")
    with _DISPATCH_PATH.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"strategy dispatch config must be a mapping: {_DISPATCH_PATH}")
    return data


def _merge_enumerator_section(section: str) -> Dict[str, Any]:
    cfg = _load_dispatch_root()
    enum_block = cfg.get("enumerator")
    if not isinstance(enum_block, dict):
        raise ValueError("strategy dispatch profile missing: 'enumerator'")
    merged: Dict[str, Any] = {}
    for field in ("reserve_cores", "max_parallel_jobs_cap"):
        if field in enum_block:
            merged[field] = enum_block[field]
    section_block = enum_block.get(section)
    if isinstance(section_block, dict):
        merged.update(section_block)
    return merged


def profile_enumerator_dispatch_config() -> Dict[str, Any]:
    return dict(_merge_enumerator_section("dispatch"))


def profile_enumerator_calendar_slice_config() -> Dict[str, Any]:
    return dict(_merge_enumerator_section("calendar_slice"))


__all__ = [
    "profile_enumerator_dispatch_config",
    "profile_enumerator_calendar_slice_config",
]
