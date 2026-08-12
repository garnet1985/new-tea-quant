"""Project-wide pytest hooks.

Refactor freeze has been lifted: tests run by default.

Environment-dependent or intentionally deferred cases should use
``pytest.mark.skip`` / ``skipif`` with an explicit reason (missing
tools/data on CI, STALE API, etc.).
"""
from __future__ import annotations

import pytest


def pytest_configure(config: pytest.Config) -> None:
    # Kept for backward compatibility with existing ``force_run`` markers.
    config.addinivalue_line(
        "markers",
        "force_run: historical opt-in during refactor freeze (no longer required)",
    )
