#!/usr/bin/env python3
"""对齐根目录 API.md 的契约测试。"""

from __future__ import annotations

import unittest

import pytest

from core.infra.system_actions import SystemActions
from core.infra.system_actions.contracts import (
    PipelineLeaseBusyError,
    VALID_KINDS,
)

pytestmark = pytest.mark.force_run


class TestSystemActionsApi(unittest.TestCase):
    def test_facade_export(self):
        import core.infra.system_actions as pkg

        self.assertEqual(pkg.__all__, ["SystemActions"])
        self.assertTrue(hasattr(SystemActions, "pipeline"))
        self.assertTrue(hasattr(SystemActions, "types"))
        self.assertFalse(hasattr(SystemActions, "scaffold"))

    def test_pipeline_methods(self):
        self.assertTrue(callable(SystemActions.pipeline.read_status))
        self.assertTrue(callable(SystemActions.pipeline.lease))

    def test_pipeline_read_status_shape(self):
        status = SystemActions.pipeline.read_status()
        self.assertIsInstance(status, dict)
        self.assertIn("busy", status)

    def test_contracts_and_types(self):
        self.assertTrue(issubclass(PipelineLeaseBusyError, Exception))
        self.assertTrue(VALID_KINDS)
        self.assertIs(SystemActions.types.VALID_KINDS, VALID_KINDS)
        self.assertIs(
            SystemActions.types.PipelineLeaseBusyError, PipelineLeaseBusyError
        )
        self.assertFalse(hasattr(SystemActions.types, "ScaffoldError"))

    def test_pipeline_lease_from_contracts_and_types(self):
        from core.infra.system_actions.contracts import PipelineLease

        self.assertTrue(callable(PipelineLease))
        self.assertIs(SystemActions.types.PipelineLease, PipelineLease)

    def test_pipeline_lease_construct(self):
        lease = SystemActions.pipeline.lease(kind="tag_run", job_id="api-smoke")
        self.assertTrue(hasattr(lease, "acquire"))
        self.assertTrue(hasattr(lease, "release"))
        self.assertTrue(hasattr(lease, "__enter__"))


if __name__ == "__main__":
    unittest.main()
