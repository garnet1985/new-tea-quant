"""对齐 API.md 的契约测试（业务行为）。"""

from __future__ import annotations

import io
import unittest
from unittest import mock

import pytest

from core.infra.cmd_layout.icon.icon import IconService

pytestmark = pytest.mark.force_run


class TestCmdLayoutApi(unittest.TestCase):
    def test_cmd_layout_facade_exported(self) -> None:
        from core.infra.cmd_layout import CmdLayout
        import core.infra.cmd_layout as pkg

        self.assertEqual(pkg.__all__, ["CmdLayout", "i"])
        for name in ("bar_chart", "title", "separator", "table", "text", "icon"):
            self.assertTrue(hasattr(CmdLayout, name), name)

    def test_title_banner_and_section(self) -> None:
        from core.infra.cmd_layout import CmdLayout

        banner = CmdLayout.title.banner("这里是标题")
        lines = banner.splitlines()
        self.assertEqual(len(lines), 3)
        self.assertEqual(lines[1], "这里是标题")
        self.assertTrue(set(lines[0]) <= {"*"})
        self.assertEqual(lines[0], lines[2])
        self.assertEqual(CmdLayout.title.section("枚举汇总"), "-- 枚举汇总 --")

    def test_title_h1_h2_h3(self) -> None:
        from core.infra.cmd_layout import CmdLayout

        h1_lines = CmdLayout.title.h1("归因对照").splitlines()
        self.assertEqual(h1_lines[0], "")
        self.assertTrue(set(h1_lines[1]) <= {"*"})
        self.assertEqual(h1_lines[2], "归因对照")

        h2_lines = CmdLayout.title.h2("参数贡献度").splitlines()
        self.assertEqual(h2_lines[0], "")
        self.assertEqual(h2_lines[1], "参数贡献度")
        self.assertTrue(set(h2_lines[2]) <= {"="})

        self.assertEqual(CmdLayout.title.h3("事实"), "--- 事实 ---")

    def test_bar_chart_render_max_bar_and_pct(self) -> None:
        from core.infra.cmd_layout import CmdLayout

        text = CmdLayout.bar_chart.render(
            [("win", 40), ("loss", 10)],
            title="胜负",
            width=20,
        )
        lines = text.splitlines()
        self.assertEqual(lines[0], "胜负")
        self.assertIn("[####################]", lines[1])
        self.assertIn("80.0%", lines[1])
        self.assertIn("20.0%", lines[2])

    def test_separator_line_variants(self) -> None:
        from core.infra.cmd_layout import CmdLayout

        self.assertEqual(CmdLayout.separator.line(width=8), "-" * 8)
        self.assertEqual(CmdLayout.separator.thick(width=6), "=" * 6)
        self.assertEqual(CmdLayout.separator.star(width=4), "*" * 4)
        self.assertEqual(CmdLayout.separator.blank(), "")

    def test_table_render(self) -> None:
        from core.infra.cmd_layout import CmdLayout

        text = CmdLayout.table.render(
            ["旋钮", "收益"],
            [["止损", "12%"]],
        )
        lines = text.splitlines()
        self.assertEqual(len(lines), 3)
        self.assertIn("旋钮", lines[0])
        self.assertIn("止损", lines[2])

    def test_text_meta_and_numbered(self) -> None:
        from core.infra.cmd_layout import CmdLayout

        self.assertEqual(
            CmdLayout.text.meta(["组 1", "对照上 2 套"]),
            "组 1 · 对照上 2 套",
        )
        self.assertEqual(
            CmdLayout.text.numbered(["先看机会", "再看资金"]),
            "1. 先看机会\n2. 再看资金",
        )
        self.assertEqual(CmdLayout.text.indent("结论"), "   结论")

    def test_icon_emoji_and_ascii_fallback(self) -> None:
        from core.infra.cmd_layout import CmdLayout

        with mock.patch.object(IconService, "supports_emoji", return_value=True):
            self.assertEqual(CmdLayout.icon.get("success"), "✅")
            self.assertEqual(CmdLayout.icon.i("ok"), "✅")
        with mock.patch.object(IconService, "supports_emoji", return_value=False):
            self.assertEqual(CmdLayout.icon.get("success"), "[OK]")

    def test_print_banner_to_stream(self) -> None:
        from core.infra.cmd_layout import CmdLayout

        buf = io.StringIO()
        returned = CmdLayout.title.print_banner("T", width=5, stream=buf)
        self.assertEqual(buf.getvalue().rstrip("\n"), returned)
        self.assertIn("T", returned)


if __name__ == "__main__":
    unittest.main()
