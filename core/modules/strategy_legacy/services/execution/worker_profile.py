"""Strategy execution dispatch 配置（读取 strategy/settings/dispatch.yaml）。"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml

_DISPATCH_PATH = Path(__file__).resolve().parents[2] / "settings" / "dispatch.yaml"


def _load_dispatch_root() -> Dict[str, Any]:
    if not _DISPATCH_PATH.is_file():
        raise FileNotFoundError(f"strategy dispatch config not found: {_DISPATCH_PATH}")
    with _DISPATCH_PATH.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"strategy dispatch config must be a mapping: {_DISPATCH_PATH}")
    return data


def _merge_profile_section(profile: str, section: str) -> Dict[str, Any]:
    cfg = _load_dispatch_root()
    profile_block = cfg.get(profile)
    if not isinstance(profile_block, dict):
        raise ValueError(f"strategy dispatch profile missing: {profile!r}")
    merged: Dict[str, Any] = {}
    for field in ("reserve_cores", "max_parallel_jobs_cap"):
        if field in profile_block:
            merged[field] = profile_block[field]
    section_block = profile_block.get(section)
    if isinstance(section_block, dict):
        merged.update(section_block)
    return merged


def profile_price_factor_dispatch_config() -> Dict[str, Any]:
    return dict(_merge_profile_section("price_factor", "dispatch"))


def profile_scanner_dispatch_config() -> Dict[str, Any]:
    return dict(_merge_profile_section("scanner", "dispatch"))


__all__ = [
    "profile_price_factor_dispatch_config",
    "profile_scanner_dispatch_config",
]
