#!/usr/bin/env python3
"""EnumeratorExecutionMode 严格解析。"""

from __future__ import annotations

import unittest

from core.modules.strategy.core.engines.enumerator.shared.fingerprint import EnumeratorExecutionMode


class TestEnumeratorExecutionMode(unittest.TestCase):
    def test_resolve_entity_based(self) -> None:
        mode = EnumeratorExecutionMode.resolve(
            {"simulation": {"execution_mode": "entity_based"}}
        )
        self.assertEqual(mode, "entity_based")

    def test_resolve_slice_based(self) -> None:
        mode = EnumeratorExecutionMode.resolve(
            {"simulation": {"execution_mode": "slice_based"}}
        )
        self.assertEqual(mode, "slice_based")

    def test_rejects_missing_simulation(self) -> None:
        with self.assertRaises(ValueError):
            EnumeratorExecutionMode.resolve({})

    def test_rejects_missing_execution_mode(self) -> None:
        with self.assertRaises(ValueError):
            EnumeratorExecutionMode.resolve({"simulation": {}})

    def test_rejects_legacy_alias(self) -> None:
        with self.assertRaises(ValueError):
            EnumeratorExecutionMode.resolve(
                {"simulation": {"execution_mode": "calendar_slice"}}
            )


if __name__ == "__main__":
    unittest.main()
