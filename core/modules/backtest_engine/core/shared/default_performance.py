"""Engine built-in performance defaults (caller dict overrides these)."""
from __future__ import annotations

from typing import Any, Dict, Optional

from core.modules.backtest_engine.core.shared.performance import (
    resolve_entity_based_performance,
    resolve_slice_based_performance,
)

ENTITY_BASED_DEFAULT_PERFORMANCE: Dict[str, Any] = resolve_entity_based_performance()
SLICE_BASED_DEFAULT_PERFORMANCE: Dict[str, Any] = resolve_slice_based_performance()


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
