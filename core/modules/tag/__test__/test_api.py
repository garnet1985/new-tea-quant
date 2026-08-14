"""API contract tests for modules.tag Facade（对齐 API.md）。"""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.modules.tag import Tag
from core.modules.tag.contracts import (
    TagCalendarAsOfResult,
    TagContext,
    TagExecutionMode,
    TagHooks,
    TagUpdateMode,
)
from core.modules.tag.core.services.discovery.data.discovered_tag import (
    DiscoveredTagInfo,
)

pytestmark = pytest.mark.force_run


def _info(
    *,
    relative: str = "demo/x",
    key: str = "x",
    enabled: bool = True,
) -> DiscoveredTagInfo:
    return DiscoveredTagInfo(
        unique_relative_path=relative,
        tag_file=Path(f"/tags/{relative}/tag.py"),
        settings_file=Path(f"/tags/{relative}/settings.py"),
        folder=Path(f"/tags/{relative}"),
        key=key,
        display_name=key,
        is_enabled=enabled,
        settings={"is_enabled": enabled, "meta": {"key": key}},
    )


class TestTagApi(unittest.TestCase):
    def test_facade_export(self) -> None:
        import core.modules.tag as pkg

        self.assertEqual(pkg.__all__, ["Tag"])
        self.assertFalse(hasattr(pkg, "TagManager"))
        self.assertFalse(hasattr(pkg, "DiscoveryService"))

    def test_public_methods(self) -> None:
        for name in ("refresh", "list_ids", "list_keys", "find", "execute"):
            self.assertTrue(callable(getattr(Tag, name)), name)
        self.assertTrue(callable(Tag.is_valid_path))
        self.assertTrue(Tag.is_valid_path("demo/market_cap_tier"))
        self.assertFalse(Tag.is_valid_path("demo/市值"))
        self.assertFalse(Tag.is_valid_path(""))

    def test_contracts(self) -> None:
        self.assertEqual(TagUpdateMode.INCREMENTAL.value, "incremental")
        self.assertEqual(TagUpdateMode.REFRESH.value, "refresh")
        self.assertEqual(TagExecutionMode.ENTITY_BASED.value, "entity_based")
        self.assertTrue(issubclass(TagHooks, object))
        self.assertEqual(TagContext.__name__, "TagContext")
        self.assertTrue(TagCalendarAsOfResult is not None)

    @patch("core.modules.tag.core.tag.DiscoveryService.discover_tags")
    @patch("core.modules.tag.core.tag.DataManager")
    def test_list_and_find(self, _dm: MagicMock, discover: MagicMock) -> None:
        discover.return_value = [
            _info(relative="demo/a", key="a", enabled=True),
            _info(relative="demo/b", key="b", enabled=False),
        ]
        tag = Tag(is_verbose=False)
        self.assertEqual(tag.list_ids(enabled_only=True), ["demo/a"])
        self.assertEqual(sorted(tag.list_ids(enabled_only=False)), ["demo/a", "demo/b"])
        self.assertEqual(tag.list_keys(enabled_only=True), ["a"])
        self.assertEqual(tag.find("a").id(), "demo/a")
        self.assertEqual(tag.find("demo/b").id(), "demo/b")
        self.assertIsNone(tag.find("missing"))


if __name__ == "__main__":
    unittest.main()
