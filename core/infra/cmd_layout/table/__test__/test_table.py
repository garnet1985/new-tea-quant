"""CmdLayout.table unit tests."""

from __future__ import annotations

import io
import unittest

import pytest

from core.infra.cmd_layout import CmdLayout
from core.infra.cmd_layout.table.table import Table
from core.infra.cmd_layout.title.title import Title

pytestmark = pytest.mark.force_run


class TestTable(unittest.TestCase):
    def test_render_aligns_first_left_others_right(self) -> None:
        text = Table.render(
            ["旋钮", "收益", "回撤"],
            [["止损", "12.0%", "-8.1%"], ["PE", "3.0%", "-2.0%"]],
        )
        lines = text.splitlines()
        self.assertEqual(len(lines), 4)
        self.assertTrue(lines[0].startswith("   "))
        self.assertIn("旋钮", lines[0])
        self.assertTrue(set(lines[1].replace(" ", "")) <= {"-"})
        self.assertIn("止损", lines[2])
        self.assertIn("12.0%", lines[2])

    def test_empty_headers(self) -> None:
        self.assertEqual(Table.render([], []), "")

    def test_cjk_column_width(self) -> None:
        text = Table.render(["名称"], [["中文名"], ["ab"]])
        lines = text.splitlines()
        # column width uses display width of 中文名 (6), not len("中文名")==3
        rule = lines[1].strip()
        self.assertEqual(len(rule), 6)
        self.assertGreater(
            Title.display_width("中文名"),
            len("中文名"),
        )

    def test_print(self) -> None:
        buf = io.StringIO()
        returned = CmdLayout.table.print(["A", "B"], [["1", "2"]], stream=buf)
        self.assertEqual(buf.getvalue().rstrip("\n"), returned)
        self.assertIn("A", returned)


if __name__ == "__main__":
    unittest.main()
