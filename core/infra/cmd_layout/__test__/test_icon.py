#!/usr/bin/env python3
"""CmdLayout.icon unit tests."""

from __future__ import annotations

import unittest
from unittest import mock

from core.infra.cmd_layout import CmdLayout, IconService, i


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
            self.assertEqual(i("success"), "✅")

    def test_ascii_fallback(self) -> None:
        with mock.patch.object(IconService, "supports_emoji", return_value=False):
            self.assertEqual(CmdLayout.icon.get("success"), "[OK]")
            self.assertEqual(CmdLayout.icon.get("error"), "[FAIL]")

    def test_unknown(self) -> None:
        self.assertEqual(CmdLayout.icon.get("no_such_icon"), "")

    def test_case_insensitive(self) -> None:
        with mock.patch.object(IconService, "supports_emoji", return_value=True):
            self.assertEqual(IconService.get("SUCCESS"), "✅")
            self.assertEqual(IconService.get("Green_Dot"), "🟢")


if __name__ == "__main__":
    unittest.main()
