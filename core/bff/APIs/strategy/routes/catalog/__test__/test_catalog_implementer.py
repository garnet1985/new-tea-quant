"""Tests for strategy catalog BFF implementer."""

from __future__ import annotations

from typing import Any, Dict, Optional
from unittest.mock import patch

from core.bff.APIs.strategy.routes.catalog.implementer import StrategyCatalogImplementer


def _info(
    *,
    path: str,
    display_name: str = "",
    is_enabled: bool = True,
    settings: Optional[Dict[str, Any]] = None,
    hooks_name: str = "DemoHooks",
) -> Dict[str, Any]:
    return {
        "unique_relative_path": path,
        "relative_path": path,
        "key": path.replace("/", "_"),
        "display_name": display_name,
        "is_enabled": is_enabled,
        "folder": f"/tmp/{path}",
        "settings": settings or {},
        "hooks_class_name": hooks_name,
    }


@patch(
    "core.bff.APIs.strategy.routes.catalog.implementer.Strategy.list_strategy_infos",
    return_value=[],
)
def test_list_strategies_empty(_mock_discover):
    catalog = StrategyCatalogImplementer().lazy_load()
    items, total = catalog.list_strategies(page=1, limit=10)
    assert items == []
    assert total == 0


@patch(
    "core.bff.APIs.strategy.routes.catalog.implementer.Strategy.list_strategy_infos"
)
def test_list_strategies_pagination_and_summary(mock_discover):
    mock_discover.return_value = [
        _info(
            path="demo/b",
            display_name="B",
            settings={
                "meta": {
                    "description": ("line1", "line2"),
                    "category": " 回归 ",
                    "keywords": ["k1", "", None, "k2"],
                    "details": {"entry": [" buy "]},
                }
            },
        ),
        _info(path="demo/a", display_name="A", is_enabled=False),
    ]

    catalog = StrategyCatalogImplementer().lazy_load()
    items, total = catalog.list_strategies(page=1, limit=1)
    assert total == 2
    assert len(items) == 1
    assert items[0]["name"] == "demo/a"
    assert items[0]["key"] == "demo_a"
    assert items[0]["display_name"] == "A"
    assert items[0]["is_enabled"] is False
    assert items[0]["worker_class_name"] == "DemoHooks"
    assert items[0]["category"] == ""

    page2, _ = catalog.list_strategies(page=2, limit=1)
    assert page2[0]["name"] == "demo/b"
    assert page2[0]["description"] == "line1line2"
    assert page2[0]["category"] == "回归"
    assert page2[0]["keywords"] == ["k1", "k2"]
    assert page2[0]["details"] == {"entry": ["buy"]}
