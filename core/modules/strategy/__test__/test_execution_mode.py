"""StrategySettings.execution_mode 严格解析（simulation.execution.mode）。"""

from __future__ import annotations

import unittest

import pytest

pytestmark = pytest.mark.force_run

from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)


class TestExecutionMode(unittest.TestCase):
    def test_entity_based(self) -> None:
        settings = StrategySettings(
            raw_settings={"simulation": {"execution": {"mode": "entity_based"}}}
        )
        self.assertEqual(settings.execution_mode, "entity_based")

    def test_slice_based(self) -> None:
        settings = StrategySettings(
            raw_settings={"simulation": {"execution": {"mode": "slice_based"}}}
        )
        self.assertEqual(settings.execution_mode, "slice_based")

    def test_defaults_mode_when_missing(self) -> None:
        settings = StrategySettings(raw_settings={"simulation": {}})
        self.assertEqual(settings.execution_mode, "entity_based")

    def test_rejects_unknown_mode(self) -> None:
        settings = StrategySettings(
            raw_settings={"simulation": {"execution": {"mode": "calendar_slice"}}}
        )
        with self.assertRaises(ValueError):
            _ = settings.execution_mode
