"""API contract tests for infra.trace Facade."""

from __future__ import annotations

import os
import unittest

import pytest

from core.infra.trace import Trace
from core.infra.trace.contracts import SendBudget, TraceConsent, TraceConfig, TraceEvent
from core.infra.trace.core.defaults import TraceDefaults

pytestmark = pytest.mark.force_run


class TestTraceApi(unittest.TestCase):
    def test_trace_facade_exported(self) -> None:
        import core.infra.trace as pkg

        self.assertEqual(pkg.__all__, ["Trace"])
        self.assertTrue(callable(Trace.track))
        self.assertTrue(callable(Trace.queue))
        self.assertTrue(callable(Trace.send))
        self.assertTrue(callable(Trace.start_background_drain))
        self.assertTrue(callable(Trace.ask_permission))
        self.assertFalse(hasattr(Trace, "flush"))
        self.assertTrue(hasattr(Trace, "config"))
        self.assertTrue(hasattr(Trace, "consent"))
        self.assertTrue(hasattr(Trace, "types"))

    def test_config_namespace(self) -> None:
        self.assertTrue(callable(Trace.config.is_enabled))
        self.assertTrue(callable(Trace.config.load))
        cfg = Trace.config.load()
        self.assertIn("enabled", cfg)
        self.assertIn("target_url", cfg)
        self.assertTrue(str(cfg["target_url"]).startswith("http"))

    def test_consent_namespace(self) -> None:
        for name in (
            "needs_ask",
            "is_decided",
            "is_granted",
            "grant",
            "revoke",
            "set",
            "read",
        ):
            self.assertTrue(callable(getattr(Trace.consent, name)))

    def test_types_and_defaults(self) -> None:
        self.assertIs(Trace.types.SendBudget, SendBudget)
        self.assertIs(Trace.types.TraceConsent, TraceConsent)
        self.assertIs(Trace.types.TraceConfig, TraceConfig)
        self.assertIs(Trace.types.TraceEvent, TraceEvent)
        self.assertIs(Trace.types.TraceDefaults, TraceDefaults)
        self.assertFalse(hasattr(Trace.types, "FlushBudget"))
        self.assertEqual(TraceConfig().target_url, TraceDefaults.TARGET_URL)

    def test_endpoint_env_override(self) -> None:
        prev = os.environ.get("NTQ_TRACE_ENDPOINT")
        try:
            os.environ["NTQ_TRACE_ENDPOINT"] = "https://override.example/api/v1/traces"
            cfg = Trace.config.load()
            self.assertEqual(cfg["target_url"], "https://override.example/api/v1/traces")
        finally:
            if prev is None:
                os.environ.pop("NTQ_TRACE_ENDPOINT", None)
            else:
                os.environ["NTQ_TRACE_ENDPOINT"] = prev


if __name__ == "__main__":
    unittest.main()
