#!/usr/bin/env python3
"""TaskGuard facade API contract tests（对齐 API.md）。"""

from __future__ import annotations

import unittest

import pytest

from core.infra.task_guard import TaskGuard
from core.infra.task_guard.contracts import (
    VALID_KINDS,
    TaskLeaseBusyError,
)

pytestmark = pytest.mark.force_run


class TestTaskGuardApi(unittest.TestCase):
    def test_facade_export(self):
        import core.infra.task_guard as pkg

        self.assertEqual(pkg.__all__, ["TaskGuard"])
        self.assertTrue(callable(TaskGuard.read_status))
        self.assertTrue(callable(TaskGuard.lease))
        self.assertTrue(hasattr(TaskGuard, "types"))

    def test_read_status_shape(self):
        status = TaskGuard.read_status()
        self.assertIn("busy", status)

    def test_contracts_and_types(self):
        self.assertTrue(issubclass(TaskLeaseBusyError, Exception))
        self.assertTrue(len(VALID_KINDS) >= 1)
        self.assertIs(TaskGuard.types.VALID_KINDS, VALID_KINDS)
        self.assertIs(TaskGuard.types.TaskLeaseBusyError, TaskLeaseBusyError)
        from core.infra.task_guard.contracts import TaskLease

        self.assertTrue(callable(TaskLease))
        self.assertIs(TaskGuard.types.TaskLease, TaskLease)

    def test_lease_construct(self):
        lease = TaskGuard.lease(kind="tag_run", job_id="api-smoke")
        self.assertEqual(lease.kind, "tag_run")
        self.assertEqual(lease.job_id, "api-smoke")


if __name__ == "__main__":
    unittest.main()
