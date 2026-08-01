"""Tests for WorkbenchVersionId / DiscoveryService.resolve_strategy_path."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.modules.strategy.core.enums import WorkbenchStep
from core.modules.strategy.core.helpers.version_id import WorkbenchVersionId
from core.modules.strategy.core.services.discovery import DiscoveryService


def test_workbench_version_id_parse():
    assert WorkbenchVersionId.parse("v3") == 3
    assert WorkbenchVersionId.parse("12") == 12
    assert WorkbenchVersionId.parse("0") is None
    assert WorkbenchVersionId.parse("") is None
    assert WorkbenchVersionId.parse("x") is None


def test_workbench_step_try_parse():
    assert WorkbenchStep.try_parse("PRICE") is WorkbenchStep.PRICE
    assert WorkbenchStep.try_parse("enumerate") is WorkbenchStep.ENUM
    assert WorkbenchStep.try_parse("capital") is None


def test_discovery_resolve_strategy_path():
    info = MagicMock()
    info.key = "demo-key"
    info.id.return_value = "demo/x"
    with patch.object(
        DiscoveryService, "discover_strategies", return_value=[info]
    ):
        assert DiscoveryService.resolve_strategy_path("demo-key") == "demo/x"
        assert DiscoveryService.resolve_strategy_path("demo/x") == "demo/x"

    with pytest.raises(ValueError):
        DiscoveryService.resolve_strategy_path("  ")

    with patch.object(DiscoveryService, "discover_strategies", return_value=[]):
        with pytest.raises(FileNotFoundError):
            DiscoveryService.resolve_strategy_path("missing")
