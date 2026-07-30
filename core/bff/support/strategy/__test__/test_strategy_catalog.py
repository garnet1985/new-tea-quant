"""Tests for strategy UI catalog (V2-02 list rows)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import patch

from core.bff.support.strategy.strategy_catalog import StrategyCatalog
from core.modules.strategy.core.services.discovery.data.discovered_strategy import (
    StrategyInfo,
)


def _info(
    *,
    path: str,
    display_name: str = "",
    is_enabled: bool = True,
    settings: Optional[Dict[str, Any]] = None,
    hooks_name: str = "DemoHooks",
) -> StrategyInfo:
    hooks = type(hooks_name, (), {})
    return StrategyInfo(
        unique_relative_path=path,
        strategy_file=Path(f"/tmp/{path}/strategy.py"),
        settings_file=Path(f"/tmp/{path}/settings.py"),
        folder=Path(f"/tmp/{path}"),
        key=path.replace("/", "_"),
        display_name=display_name,
        is_enabled=is_enabled,
        settings=settings or {},
        hooks_class=hooks,
        hooks_module_path="mod",
    )


@patch(
    "core.bff.support.strategy.strategy_catalog.DiscoveryService.discover_strategies",
    return_value=[],
)
def test_fetch_page_empty(_mock_discover):
    items, total = StrategyCatalog.fetch_discovered_strategies_page(page=1, limit=10)
    assert items == []
    assert total == 0


@patch(
    "core.bff.support.strategy.strategy_catalog.DiscoveryService.discover_strategies"
)
def test_fetch_page_pagination_and_summary(mock_discover):
    mock_discover.return_value = [
        _info(
            path="demo/b",
            display_name="B",
            settings={
                "meta": {
                    "description": ("line1", "line2"),
                    "keywords": ["k1", "", None, "k2"],
                    "details": {"entry": [" buy "]},
                }
            },
        ),
        _info(path="demo/a", display_name="A", is_enabled=False),
    ]

    items, total = StrategyCatalog.fetch_discovered_strategies_page(page=1, limit=1)
    assert total == 2
    assert len(items) == 1
    assert items[0]["name"] == "demo/a"
    assert items[0]["display_name"] == "A"
    assert items[0]["is_enabled"] is False
    assert items[0]["worker_class_name"] == "DemoHooks"

    page2, _ = StrategyCatalog.fetch_discovered_strategies_page(page=2, limit=1)
    assert page2[0]["name"] == "demo/b"
    assert page2[0]["description"] == "line1line2"
    assert page2[0]["keywords"] == ["k1", "k2"]
    assert page2[0]["details"] == {"entry": ["buy"]}
