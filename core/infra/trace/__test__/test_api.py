"""API contract tests for infra.trace Facade."""

from __future__ import annotations

import unittest

import pytest

pytestmark = pytest.mark.force_run


class TestTraceApi(unittest.TestCase):
    def test_trace_facade_exported(self) -> None:
        from core.infra.trace import Trace
        import core.infra.trace as pkg

        self.assertEqual(pkg.__all__, ["Trace"])
        self.assertTrue(callable(Trace.track))
        self.assertTrue(callable(Trace.flush))
        self.assertTrue(callable(Trace.start_background_drain))
        self.assertTrue(callable(Trace.ask_permission))
        self.assertTrue(hasattr(Trace, "config"))
        self.assertTrue(hasattr(Trace, "consent"))
        self.assertTrue(callable(Trace.consent.needs_ask))
        self.assertTrue(callable(Trace.consent.is_decided))
        self.assertTrue(callable(Trace.consent.set))

    def test_config_namespace(self) -> None:
        from core.infra.trace import Trace

        self.assertTrue(callable(Trace.config.is_enabled))
        self.assertTrue(callable(Trace.config.load))
        cfg = Trace.config.load()
        self.assertIn("enabled", cfg)
        self.assertIn("target_url", cfg)


if __name__ == "__main__":
    unittest.main()
