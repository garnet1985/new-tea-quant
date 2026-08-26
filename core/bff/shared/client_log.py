"""Non-fatal degraded paths (poll, hydrate, catalog enrichment): always log."""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger("bff.client")


def log_degraded(
    scope: str,
    exc: Optional[BaseException] = None,
    detail: str = "",
) -> None:
    """Log a swallowed/degraded failure without raising."""
    message = detail.strip() or (str(exc).strip() if exc else "") or "unknown"
    if exc is not None:
        logger.warning("[client:%s] %s", scope, message, exc_info=exc)
        return
    logger.warning("[client:%s] %s", scope, message)
