"""API contract tests for infra.trace Facade."""

from __future__ import annotations

import unittest

import pytest

from core.infra.trace import Trace
from core.infra.trace.contracts import FlushBudget, TraceConsent, TraceConfig, TraceEvent

pytestmark = pytest.mark.force_run


class TestTraceApi(unittest.TestCase):
    def test_trace_facade_exported(self) -> None:
        import core.infra.trace as pkg

        self.assertEqual(pkg.__all__, ["Trace"])
        self.assertTrue(callable(Trace.track))
        self.assertTrue(callable(Trace.flush))
        self.assertTrue(callable(Trace.start_background_drain))
        self.assertTrue(callable(Trace.ask_permission))
        self.assertTrue(hasattr(Trace, "config"))
        self.assertTrue(hasattr(Trace, "consent"))

    def test_config_namespace(self) -> None:
        self.assertTrue(callable(Trace.config.is_enabled))
        self.assertTrue(callable(Trace.config.load))
        cfg = Trace.config.load()
        self.assertIn("enabled", cfg)
        self.assertIn("target_url", cfg)

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

    def test_contracts_symbols(self) -> None:
        self.assertTrue(issubclass(FlushBudget, str))
        self.assertTrue(hasattr(TraceConsent, "to_dict"))
        self.assertTrue(hasattr(TraceConfig, "__dataclass_fields__"))
        self.assertTrue(hasattr(TraceEvent, "to_wire_dict"))


if __name__ == "__main__":
    unittest.main()
