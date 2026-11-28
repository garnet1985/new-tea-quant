"""Shared discovery defaults (module-internal)."""

from __future__ import annotations

DEFAULT_SKIP_MODULES: frozenset[str] = frozenset({"__pycache__", "__init__"})

__all__ = ["DEFAULT_SKIP_MODULES"]