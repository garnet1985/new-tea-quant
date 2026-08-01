#!/usr/bin/env python3
"""CmdLayout.title / separator unit tests."""

from __future__ import annotations

import io
import unittest

import pytest

from core.infra.cmd_layout import CmdLayout
from core.infra.cmd_layout.title import Title, display_width
from core.infra.cmd_layout.separator import Separator

pytestmark = pytest.mark.force_run


class TestTitle(unittest.TestCase):
    def test_facade_export(self) -> None:
        self.assertTrue(hasattr(CmdLayout, "title"))
        self.assertTrue(callable(CmdLayout.title.banner))
        self.assertTrue(callable(CmdLayout.title.section))
        self.assertTrue(callable(CmdLayout.title.print_banner))
        self.assertTrue(callable(CmdLayout.title.print_section))

    def test_banner_wraps_with_stars(self) -> None:
        text = Title.banner("这里是标题")
        lines = text.splitlines()
        self.assertEqual(len(lines), 3)
        expected = display_width("这里是标题") + Title.DEFAULT_BANNER_PAD
        self.assertEqual(lines[0], "*" * expected)
        self.assertEqual(lines[1], "这里是标题")
        self.assertEqual(lines[2], lines[0])
        self.assertTrue(set(lines[0]) <= {"*"})

    def test_banner_fixed_width_and_center(self) -> None:
        text = Title.banner("Hi", width=10, center=True)
        lines = text.splitlines()
        self.assertEqual(lines[0], "*" * 10)
        self.assertEqual(len(lines[1]), 10)
        self.assertIn("Hi", lines[1])

    def test_section(self) -> None:
        self.assertEqual(Title.section("枚举汇总"), "-- 枚举汇总 --")
        self.assertEqual(Title.section("ROI", char="="), "== ROI ==")

    def test_print_banner(self) -> None:
        buf = io.StringIO()
        returned = CmdLayout.title.print_banner("T", width=5, stream=buf)
        self.assertEqual(buf.getvalue().rstrip("\n"), returned)
        self.assertIn("T", returned)


class TestSeparator(unittest.TestCase):
    def test_facade_export(self) -> None:
        self.assertTrue(hasattr(CmdLayout, "separator"))
        for name in (
            "line",
            "thick",
            "star",
            "blank",
            "print_line",
            "print_thick",
            "print_star",
            "print_blank",
        ):
            self.assertTrue(callable(getattr(CmdLayout.separator, name)))

    def test_line_variants(self) -> None:
        self.assertEqual(Separator.line(width=8), "-" * 8)
        self.assertEqual(Separator.thick(width=6), "=" * 6)
        self.assertEqual(Separator.star(width=4), "*" * 4)
        self.assertEqual(Separator.blank(), "")

    def test_ascii_only(self) -> None:
        for text in (
            Separator.line(width=20),
            Separator.thick(width=20),
            Separator.star(width=20),
            Title.banner("OK", width=20),
            Title.section("section"),
        ):
            self.assertTrue(all(ord(ch) < 128 or ch in text for ch in text if ch != "\n"))
            # no box-drawing defaults
            self.assertNotIn("─", text)
            self.assertNotIn("═", text)

    def test_print_line(self) -> None:
        buf = io.StringIO()
        returned = CmdLayout.separator.print_line(width=5, stream=buf)
        self.assertEqual(returned, "-----")
        self.assertEqual(buf.getvalue(), "-----\n")

    def test_print_blank(self) -> None:
        buf = io.StringIO()
        returned = CmdLayout.separator.print_blank(stream=buf)
        self.assertEqual(returned, "")
        self.assertEqual(buf.getvalue(), "\n")


if __name__ == "__main__":
    unittest.main()
