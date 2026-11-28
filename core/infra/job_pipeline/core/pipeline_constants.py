"""Job pipeline runtime defaults (module-internal SSOT)."""

from __future__ import annotations

FILE_LOCK_TIMEOUT_SEC: float = 5.0
DEFAULT_MAX_PENDING: int = 8
STALE_AFTER_PROGRESS_SEC: int = 2 * 60 * 60
STALE_AFTER_NO_PROGRESS_SEC: int = 12 * 60 * 60

__all__ = [
    "DEFAULT_MAX_PENDING",
    "FILE_LOCK_TIMEOUT_SEC",
    "STALE_AFTER_NO_PROGRESS_SEC",
    "STALE_AFTER_PROGRESS_SEC",
]