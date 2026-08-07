"""CLI environment flag helpers."""

from __future__ import annotations

import os


class CliEnv:
    """Shared env-var names and truthy parsing for CLI bootstrap / commands."""

    SKIP_AUTO_VENV = "NTQ_SKIP_AUTO_VENV"
    SKIP_AUTO_INSTALL = "NTQ_SKIP_AUTO_INSTALL"
    UPDATE_ASSUME_YES = "NTQ_UPDATE_ASSUME_YES"

    _TRUTHY = frozenset({"1", "true", "yes"})

    @classmethod
    def is_truthy(cls, name: str) -> bool:
        return os.environ.get(name, "").strip().lower() in cls._TRUTHY
