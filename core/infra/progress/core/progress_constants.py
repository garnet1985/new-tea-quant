"""Progress runtime defaults and env keys (module-internal SSOT)."""

from __future__ import annotations

ENV_PROGRESS_DIR = "NTQ_PROGRESS_DIR"
ENV_FLUSH_DELAY = "NTQ_PROGRESS_FLUSH_DELAY"

DEFAULT_FLUSH_DELAY_SEC: float = 0.2
KEEP_FINISHED_ROOTS: int = 20
KEEP_FINISHED_DAYS: int = 14

PYTEST_PROGRESS_SUBDIR = "ntq-progress-pytest"
FALLBACK_PROGRESS_SUBDIR = "ntq-progress"
USERSPACE_PROGRESS_SEGMENT = "progress"

TERMINAL_STATUSES = frozenset({"completed", "failed", "cancelled"})
PASSED_STATUSES = frozenset({"completed", "failed"})

__all__ = [
    "DEFAULT_FLUSH_DELAY_SEC",
    "ENV_FLUSH_DELAY",
    "ENV_PROGRESS_DIR",
    "FALLBACK_PROGRESS_SUBDIR",
    "KEEP_FINISHED_DAYS",
    "KEEP_FINISHED_ROOTS",
    "PASSED_STATUSES",
    "PYTEST_PROGRESS_SUBDIR",
    "TERMINAL_STATUSES",
    "USERSPACE_PROGRESS_SEGMENT",
]