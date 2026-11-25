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
        self.assertTrue(callable(PostProcess.summarize_adapter))
        self.assertTrue(callable(PostProcess.list_adapter_summaries))
        self.assertTrue(callable(PostProcess.check_adapter_readiness))
        ok, err = PostProcess.validate_adapter("")
        self.assertFalse(ok)
        self.assertTrue(err)

    def test_post_process_apis(self) -> None:
        self.assertTrue(callable(PostProcess.list_post_processors))
        self.assertTrue(callable(PostProcess.list_enabled_post_processors))
        self.assertTrue(callable(PostProcess.validate_post_processor))
        self.assertTrue(callable(PostProcess.load_post_processor))
        self.assertTrue(callable(PostProcess.summarize_post_processor))
        self.assertTrue(callable(PostProcess.list_post_processor_summaries))
        self.assertTrue(callable(PostProcess.set_enabled))
        self.assertTrue(callable(PostProcess.update_post_processor_adapters))
        self.assertTrue(callable(PostProcess.run_post_processor))
        self.assertTrue(callable(PostProcess.run_enabled_post_processors))
        ok, err = PostProcess.validate_post_processor("")
        self.assertFalse(ok)
        self.assertTrue(err)

    def test_catalog_summaries(self) -> None:
        adapters = PostProcess.list_adapter_summaries()
        self.assertTrue(any(row.get("name") == "presenter" for row in adapters))
        presenter = PostProcess.summarize_adapter("presenter")
        self.assertIsNotNone(presenter)
        assert presenter is not None
        self.assertIn("supports_dry_run", presenter)
        self.assertIn("display_name", presenter)
        self.assertIn("status", presenter)
        self.assertIn("readiness", presenter)
        self.assertEqual(presenter.get("status"), "live")
        self.assertTrue(str(presenter.get("display_name") or "").strip())

        email = PostProcess.check_adapter_readiness("email_sender")
        # 缺 to / token → 不可用优先于 dry_run
        self.assertEqual(email.get("status"), "unavailable")
        self.assertFalse(email.get("ok"))
        self.assertIn("缺少", str(email.get("remark") or ""))
        email_ready = PostProcess.check_adapter_readiness(
            "email_sender",
            config={"dry_run": True, "to": ["a@b.com"]},
        )
        # 仍缺 token.txt → 依旧 unavailable
        self.assertEqual(email_ready.get("status"), "unavailable")
        demo = PostProcess.check_adapter_readiness("demo_broker")
        self.assertEqual(demo.get("status"), "dry_run")
        self.assertEqual(demo.get("remark"), "当前是测试模式")

        self.assertIn("ntq_email", PostProcess.list_adapters())
        from unittest.mock import patch

        with patch(
            "core.infra.membership.Membership.read",
            return_value=None,
        ):
            ntq_mail = PostProcess.check_adapter_readiness("ntq_email")
        # 无会员凭证 → 不可用
        self.assertEqual(ntq_mail.get("status"), "unavailable")
        self.assertIn("会员凭证", str(ntq_mail.get("remark") or ""))

        processors = PostProcess.list_post_processor_summaries()
        self.assertTrue(any(row.get("key") == "presenter" for row in processors))
        pp = PostProcess.summarize_post_processor("presenter")
        self.assertIsNotNone(pp)
        assert pp is not None
        self.assertIn("execution_order", pp)
        self.assertTrue(pp.get("adapters"))
        self.assertIn("status", pp["adapters"][0])
        self.assertNotIn("dry_run_summary", pp)

    def test_presenter_adapter_and_post_process_available(self) -> None:
        self.assertIn("presenter", PostProcess.list_adapters())
        ok, err = PostProcess.validate_adapter("presenter")
        self.assertTrue(ok, err)
        self.assertIn("presenter", PostProcess.list_post_processors())
        ok2, err2 = PostProcess.validate_post_processor("presenter")
        self.assertTrue(ok2, err2)
        enabled = PostProcess.list_enabled_post_processors()
        # 默认开 ntq_mail（含 presenter 步骤）；单独 presenter / demo_handoff 关闭
        self.assertIn("ntq_mail", enabled)
        self.assertNotIn("presenter", enabled)
        self.assertNotIn("demo_handoff", enabled)

    def test_build_and_run_presenter_post_process(self) -> None:
        session = PostProcess.build_session_report(
            scan_date="20240110",
            strategy_name="demo",
            opportunities=[],
            goal={"stop_loss": []},
        )
        ok, err = PostProcess.validate_session(session)
        self.assertTrue(ok, err)
        out = PostProcess.run_enabled_post_processors(session)
        self.assertIsInstance(out, dict)
        self.assertIn("ntq_mail", out.get("ran") or [])
        # ntq_mail 含 presenter 步骤 → 扫描页 UI 槽（SPECIAL-CASE DEC-05）
        ui = out.get("ui") or {}
        scan_report = ui.get("scan_report") or {}
        self.assertEqual(scan_report.get("view"), "presenter")
        props = scan_report.get("props") or {}
        self.assertIn("strategies", props)
        self.assertIn("backtest_history", props)

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
