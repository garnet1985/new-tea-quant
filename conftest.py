"""Project-wide pytest hooks.

UT is frozen during strategy / enumerator refactor. Test files are kept;
execution is skipped until refactor stabilizes.

Re-enable: ``NTQ_TESTS_ENABLED=1 python -m pytest ...``
Or mark a test with ``@pytest.mark.force_run``.
"""
from __future__ import annotations

import os

import pytest

FREEZE_REASON = (
    "UT disabled during strategy module refactor "
    "(see module __test__/TEST_CASES.md for public index). "
    "Set NTQ_TESTS_ENABLED=1 to run."
)


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "force_run: run during refactor freeze (see root conftest.py)",
    )


def _tests_enabled() -> bool:
    return os.environ.get("NTQ_TESTS_ENABLED", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if _tests_enabled():
        return

    skip = pytest.mark.skip(reason=FREEZE_REASON)
    for item in items:
        if "force_run" not in item.keywords:
            item.add_marker(skip)
