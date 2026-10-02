#!/usr/bin/env python3
"""CmdLayout.title unit tests."""

from __future__ import annotations

import io
import unittest

import pytest

from core.infra.cmd_layout import CmdLayout
from core.infra.cmd_layout.title.title import Title

pytestmark = pytest.mark.force_run


class TestTitle(unittest.TestCase):
    def test_banner_wraps_with_stars(self) -> None:
        text = Title.banner("这里是标题")
        lines = text.splitlines()
        self.assertEqual(len(lines), 3)
        expected = Title.display_width("这里是标题") + Title.DEFAULT_BANNER_PAD
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

    def test_h1_blank_star_box(self) -> None:
        text = Title.h1("归因对照")
        lines = text.splitlines()
        self.assertEqual(lines[0], "")
        self.assertTrue(set(lines[1]) <= {"*"})
        self.assertEqual(lines[2], "归因对照")
        self.assertEqual(lines[3], lines[1])

    def test_h2_underline(self) -> None:
        text = Title.h2("参数贡献度")
        lines = text.splitlines()
        self.assertEqual(lines[0], "")
        self.assertEqual(lines[1], "参数贡献度")
        self.assertTrue(set(lines[2]) <= {"="})
        self.assertGreaterEqual(len(lines[2]), Title.DEFAULT_H2_MIN_WIDTH)
        self.assertGreaterEqual(len(lines[2]), Title.display_width("参数贡献度"))

    def test_h3_triple_dash(self) -> None:
        self.assertEqual(Title.h3("事实"), "--- 事实 ---")

    def test_print_h3_adds_blank(self) -> None:
        buf = io.StringIO()
        returned = CmdLayout.title.print_h3("结论", stream=buf)
        self.assertEqual(returned, "--- 结论 ---")
        self.assertEqual(buf.getvalue(), "--- 结论 ---\n\n")

    def test_print_banner(self) -> None:
        buf = io.StringIO()
        returned = CmdLayout.title.print_banner("T", width=5, stream=buf)
        self.assertEqual(buf.getvalue().rstrip("\n"), returned)
        self.assertIn("T", returned)



if __name__ == "__main__":
    unittest.main()
