"""Tag API contract tests（骨架，对齐 api.yaml）。"""

from __future__ import annotations

import unittest

import pytest

pytestmark = pytest.mark.force_run


class TestApi(unittest.TestCase):
    def test_facade_export(self):
        from core.modules.tag import Tag

        self.assertTrue(callable(Tag))

    def test_execute_api(self):
        from core.modules.tag import Tag

        self.assertTrue(callable(Tag.execute))

    def test_list_keys_api(self):
        from core.modules.tag import Tag

        self.assertTrue(callable(Tag.list_keys))

    def test_find_api(self):
        from core.modules.tag import Tag

        self.assertTrue(callable(Tag.find))


class TestContracts(unittest.TestCase):
    def test_hooks_export(self):
        from core.modules.tag import Tag
        from core.modules.tag.contracts import (
            TagCalendarAsOfResult,
            TagContext,
            TagHooks,
            TagUpdateMode,
        )

        self.assertTrue(TagHooks is not None)
        self.assertTrue(TagContext is not None)
        self.assertTrue(TagCalendarAsOfResult is not None)

    def test_update_mode_enum(self):
        from core.modules.tag.contracts import TagUpdateMode

        self.assertEqual(TagUpdateMode.INCREMENTAL.value, "incremental")
        self.assertEqual(TagUpdateMode.REFRESH.value, "refresh")
