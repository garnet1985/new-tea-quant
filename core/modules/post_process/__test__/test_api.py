"""API contract tests for modules.post_process Facade."""

from __future__ import annotations

import unittest

import pytest

from core.modules.post_process import PostProcess
from core.modules.post_process.contracts import (
    BaseAdapter,
    Opportunity,
    ScanSessionReport,
    StrategyScanReport,
)

pytestmark = pytest.mark.force_run


class TestAdapterApi(unittest.TestCase):
    def test_facade_export(self) -> None:
        import core.modules.post_process as pkg

        self.assertEqual(pkg.__all__, ["PostProcess"])
        self.assertFalse(hasattr(pkg, "BaseOpportunityAdapter"))
        self.assertFalse(hasattr(pkg, "BaseAdapter"))

    def test_component_apis(self) -> None:
        self.assertTrue(callable(PostProcess.list_adapters))
        self.assertTrue(callable(PostProcess.validate_adapter))
        self.assertTrue(callable(PostProcess.load_adapter_class))
        ok, err = PostProcess.validate_adapter("")
        self.assertFalse(ok)
        self.assertTrue(err)

    def test_post_process_apis(self) -> None:
        self.assertTrue(callable(PostProcess.list_post_processors))
        self.assertTrue(callable(PostProcess.validate_post_processor))
        self.assertTrue(callable(PostProcess.load_post_processor))
        self.assertTrue(callable(PostProcess.run_post_processor))
        ok, err = PostProcess.validate_post_processor("")
        self.assertFalse(ok)
        self.assertTrue(err)

    def test_console_component_and_post_process_available(self) -> None:
        self.assertIn("console", PostProcess.list_adapters())
        ok, err = PostProcess.validate_adapter("console")
        self.assertTrue(ok, err)
        self.assertIn("console", PostProcess.list_post_processors())
        ok2, err2 = PostProcess.validate_post_processor("console")
        self.assertTrue(ok2, err2)

    def test_build_and_run_console_post_process(self) -> None:
        session = PostProcess.build_session_report(
            scan_date="20240110",
            strategy_name="demo",
            opportunities=[],
            goal={"stop_loss": []},
        )
        ok, err = PostProcess.validate_session(session)
        self.assertTrue(ok, err)
        PostProcess.run_post_processor("console", session)

    def test_contracts(self) -> None:
        self.assertTrue(issubclass(BaseAdapter, object))
        opp = Opportunity(
            id="x",
            entity_id="000001.SZ",
            trigger_date="20240110",
            trigger_price=10.0,
        )
        ok, _ = opp.validate()
        self.assertTrue(ok)
        rep = StrategyScanReport(
            strategy_name="demo",
            scan_date="20240110",
            opportunities=[opp],
        )
        session = ScanSessionReport(scan_date="20240110", strategies=[rep])
        ok2, _ = session.validate()
        self.assertTrue(ok2)


if __name__ == "__main__":
    unittest.main()
