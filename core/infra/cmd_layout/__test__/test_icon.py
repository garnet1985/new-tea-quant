#!/usr/bin/env python3
"""CmdLayout.icon unit tests."""

from __future__ import annotations

import unittest
from unittest import mock

import pytest

from core.infra.cmd_layout import CmdLayout
from core.infra.cmd_layout.icon import IconService

pytestmark = pytest.mark.force_run


class TestIcon(unittest.TestCase):
    def test_facade_export(self) -> None:
        self.assertTrue(hasattr(CmdLayout, "icon"))
        self.assertTrue(callable(CmdLayout.icon.get))
        self.assertTrue(callable(CmdLayout.icon.i))
        self.assertTrue(callable(CmdLayout.icon.supports_emoji))

    def test_get_aliases(self) -> None:
        with mock.patch.object(IconService, "supports_emoji", return_value=True):
            self.assertEqual(CmdLayout.icon.get("success"), "✅")
            self.assertEqual(CmdLayout.icon.get("ok"), "✅")
            self.assertEqual(CmdLayout.icon.i("chart"), "📊")

    def test_ascii_fallback(self) -> None:
        with mock.patch.object(IconService, "supports_emoji", return_value=False):
            self.assertEqual(CmdLayout.icon.get("success"), "[OK]")
            self.assertEqual(CmdLayout.icon.get("error"), "[FAIL]")

    def test_unknown(self) -> None:
        self.assertEqual(CmdLayout.icon.get("no_such_icon"), "")

    def test_case_insensitive(self) -> None:
        with mock.patch.object(IconService, "supports_emoji", return_value=True):
            self.assertEqual(CmdLayout.icon.get("SUCCESS"), "✅")
            self.assertEqual(CmdLayout.icon.get("Green_Dot"), "🟢")


if __name__ == "__main__":
    unittest.main()
