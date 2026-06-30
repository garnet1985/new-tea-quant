"""Tag 模块 dispatch 配置（读取 tag/settings/dispatch.yaml）。"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml

_DISPATCH_PATH = Path(__file__).with_name("dispatch.yaml")


def _load_dispatch_root() -> Dict[str, Any]:
    if not _DISPATCH_PATH.is_file():
        raise FileNotFoundError(f"tag dispatch config not found: {_DISPATCH_PATH}")
    with _DISPATCH_PATH.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"tag dispatch config must be a mapping: {_DISPATCH_PATH}")
    return data


def _merge_dispatch_section(section: str) -> Dict[str, Any]:
    cfg = _load_dispatch_root()
    merged: Dict[str, Any] = {}
    default_block = cfg.get("default")
    if isinstance(default_block, dict):
        merged.update(default_block)
    section_block = cfg.get(section)
    if isinstance(section_block, dict):
        merged.update(section_block)
    return merged


def profile_tag_entity_timeline_config() -> Dict[str, Any]:
    """entity_timeline dispatch（性能基准，用户不可覆盖）。"""
    return dict(_merge_dispatch_section("entity_timeline"))


def profile_tag_calendar_slice_config() -> Dict[str, Any]:
    """calendar_slice dispatch（性能基准，用户不可覆盖）。"""
    return dict(_merge_dispatch_section("calendar_slice"))


__all__ = [
    "profile_tag_entity_timeline_config",
    "profile_tag_calendar_slice_config",
]
