#!/usr/bin/env python3
"""对齐根目录 API.md 的契约测试。"""

from __future__ import annotations

import unittest

import pytest

from core.infra.system_actions import SystemActions
from core.infra.system_actions.contracts import (
    PipelineLeaseBusyError,
    ScaffoldError,
    ScaffoldResult,
    VALID_KINDS,
)

pytestmark = pytest.mark.force_run


class TestSystemActionsApi(unittest.TestCase):
    def test_facade_export(self):
        import core.infra.system_actions as pkg

        self.assertEqual(pkg.__all__, ["SystemActions"])
        self.assertTrue(hasattr(SystemActions, "cache"))
        self.assertTrue(hasattr(SystemActions, "pipeline"))
        self.assertTrue(hasattr(SystemActions, "scaffold"))

    def test_cache_methods(self):
        for name in (
            "run",
            "clear_workbench_db",
            "clear_backtest_results",
            "clear_scan_results",
            "clear_strategy_results",
            "clear_userspace_ntq",
        ):
            self.assertTrue(callable(getattr(SystemActions.cache, name)))

    def test_pipeline_methods(self):
        self.assertTrue(callable(SystemActions.pipeline.read_status))
        self.assertTrue(callable(SystemActions.pipeline.lease))

    def test_scaffold_methods(self):
        self.assertTrue(callable(SystemActions.scaffold.create_strategy))
        self.assertTrue(callable(SystemActions.scaffold.create_tag))

    def test_pipeline_read_status_shape(self):
        status = SystemActions.pipeline.read_status()
        self.assertIsInstance(status, dict)
        self.assertIn("busy", status)

    def test_cache_run_nothing_selected(self):
        out = SystemActions.cache.run()
        self.assertEqual(out.get("ok"), False)
        self.assertEqual(out.get("error"), "nothing_selected")

    def test_contracts_symbols(self):
        self.assertTrue(issubclass(ScaffoldError, ValueError))
        self.assertTrue(issubclass(PipelineLeaseBusyError, Exception))
        self.assertTrue(VALID_KINDS)
        self.assertTrue(hasattr(ScaffoldResult, "__dataclass_fields__"))

    def test_pipeline_lease_from_contracts(self):
        from core.infra.system_actions.contracts import PipelineLease

        self.assertTrue(callable(PipelineLease))


if __name__ == "__main__":
    unittest.main()
