"""Engine built-in performance defaults (caller dict overrides these)."""
from __future__ import annotations

from typing import Any, Dict, Optional

ENTITY_BASED_DEFAULT_PERFORMANCE: Dict[str, Any] = {
    "max_workers": "auto",
    "entities_per_job": "auto",
    "dispatch_probe": True,
    "prefetch_ahead": 1,
}

SLICE_BASED_DEFAULT_PERFORMANCE: Dict[str, Any] = {
    "reader_workers": "auto",
    "queue_depth": "auto",
    "prefetch_enabled": True,
    "slice_open_days": "auto",
    "queue_capacity": "auto",
    "preload_depth": "auto",
    "compute_processes": 1,
}


def merge_performance(
    defaults: Dict[str, Any],
    override: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    merged = dict(defaults)
    if override:
        merged.update(override)
    return merged


__all__ = [
    "ENTITY_BASED_DEFAULT_PERFORMANCE",
    "SLICE_BASED_DEFAULT_PERFORMANCE",
    "merge_performance",
]
