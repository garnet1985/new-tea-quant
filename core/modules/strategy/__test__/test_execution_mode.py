#!/usr/bin/env python3
"""StrategySettings.execution_mode 严格解析。"""

from __future__ import annotations

import unittest

from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import StrategySettings


class TestStrategySettingsExecutionMode(unittest.TestCase):
    def test_entity_based(self) -> None:
        settings = StrategySettings(
            raw_settings={"simulation": {"execution_mode": "entity_based"}}
        )
        self.assertEqual(settings.execution_mode, "entity_based")
        self.assertTrue(settings.is_entity_based)
        self.assertFalse(settings.is_slice_based)

    def test_slice_based(self) -> None:
        settings = StrategySettings(
            raw_settings={"simulation": {"execution_mode": "slice_based"}}
        )
        self.assertEqual(settings.execution_mode, "slice_based")
        self.assertTrue(settings.is_slice_based)
        self.assertFalse(settings.is_entity_based)

    def test_rejects_missing_simulation(self) -> None:
        with self.assertRaises(ValueError):
            StrategySettings(raw_settings={}).execution_mode

    def test_rejects_missing_execution_mode(self) -> None:
        with self.assertRaises(ValueError):
            StrategySettings(raw_settings={"simulation": {}}).execution_mode

    def test_rejects_legacy_alias(self) -> None:
        with self.assertRaises(ValueError):
            StrategySettings(
                raw_settings={"simulation": {"execution_mode": "calendar_slice"}}
            ).execution_mode


if __name__ == "__main__":
    unittest.main()
