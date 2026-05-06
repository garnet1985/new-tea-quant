"""Discover userspace strategies and return lightweight list rows (launcher / BED)."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from core.modules.strategy.engines.shared.data_classes.discovered_strategy import (
    DiscoveredStrategy,
)
from core.modules.strategy.services.discovery import StrategyDiscoveryHelper


def _summary(ds: DiscoveredStrategy) -> Dict[str, Any]:
    """``DiscoveredStrategy`` → JSON-safe summary for list APIs."""
    return {
        "name": ds.name,
        "is_enabled": bool(ds.is_enabled),
        "worker_class_name": ds.worker_class_name,
        "folder": str(ds.folder),
    }


def fetch_discovered_strategies_page(page: int, limit: int) -> Tuple[List[Dict[str, Any]], int]:
    """
    Return a page of discovered strategies and total count.

    ``page`` is 1-based. Strategies are sorted by ``name``.
    """
    discovered = StrategyDiscoveryHelper.discover_strategies()
    ordered = sorted(discovered.values(), key=lambda d: d.name)
    total = len(ordered)
    if total == 0:
        return [], 0
    page = max(1, int(page))
    limit = max(1, int(limit))
    start = (page - 1) * limit
    chunk = ordered[start : start + limit]
    return [_summary(ds) for ds in chunk], total
