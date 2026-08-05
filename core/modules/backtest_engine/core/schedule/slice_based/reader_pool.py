"""Slice reader pool (SOT: R readers + queue depth N).

v1: sync loader wrapper used by Strategy per formal slice.
Multiprocess enqueue (R>0) lands when BE owns window orchestration end-to-end;
until then Strategy calls ``load_window`` in the compute process (R=0 serial path).
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class SliceReaderPool:
    """BE-owned API for per-slice per-entity loads.

    All entry points are classmethods / instance methods on this class
    (no free-function algorithm exports).
    """

    def __init__(
        self,
        *,
        reader_workers: int,
        queue_depth: int,
    ) -> None:
        self.reader_workers = max(0, int(reader_workers))
        self.queue_depth = max(0, int(queue_depth))
        if self.reader_workers > 0:
            logger.info(
                "SliceReaderPool: reader_workers=%s queue_depth=%s "
                "(multiprocess enqueue not wired yet; loads stay sync in compute)",
                self.reader_workers,
                self.queue_depth,
            )

    @classmethod
    def from_plan(cls, plan: Any) -> "SliceReaderPool":
        return cls(
            reader_workers=int(getattr(plan, "reader_workers", 0) or 0),
            queue_depth=int(
                getattr(plan, "preload_depth", None)
                or getattr(plan, "queue_capacity", 0)
                or 0
            ),
        )

    def load_window(
        self,
        payload: Dict[str, Any],
        *,
        start: str,
        end: str,
        perf: Any = None,
    ) -> Dict[str, Any]:
        """Load one per-entity window (sync). Returns ``entity_contracts``."""
        from core.modules.strategy.core.services.entity_loader.job_bundle_loader import (
            JobBundleLoader,
        )

        return JobBundleLoader.load_per_entity_window(
            payload,
            start=start,
            end=end,
            perf=perf,
        )


__all__ = ["SliceReaderPool"]
