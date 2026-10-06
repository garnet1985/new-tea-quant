"""CmdLayout.text unit tests."""

from __future__ import annotations

import io
import unittest

import pytest

from core.infra.cmd_layout import CmdLayout
from core.infra.cmd_layout.text.text import Text

pytestmark = pytest.mark.force_run


class TestText(unittest.TestCase):
    def test_meta_joins_non_empty(self) -> None:
        self.assertEqual(
            Text.meta(["组 3", "", "对照上 4 套", None]),
            "组 3 · 对照上 4 套",
        )

    def test_kv(self) -> None:
        self.assertEqual(Text.kv("version", "1-1"), "version: 1-1")

    def test_indent(self) -> None:
        self.assertEqual(Text.indent("一句话结论"), "   一句话结论")
        self.assertEqual(Text.indent("a\nb", spaces=2), "  a\n  b")

    def test_numbered_and_bullets(self) -> None:
        self.assertEqual(
            Text.numbered(["先看机会", "再看资金"]),
            "1. 先看机会\n2. 再看资金",
        )
        self.assertEqual(
            Text.bullets(["A", "B"], indent=3),
            "   - A\n   - B",
        )
        self.assertEqual(
            Text.numbered([], empty="没有建议"),
            "没有建议",
        )

    def test_print_indent(self) -> None:
        buf = io.StringIO()
        returned = CmdLayout.text.print_indent("hi", stream=buf)
        self.assertEqual(returned, "   hi")
        self.assertEqual(buf.getvalue(), "   hi\n")


if __name__ == "__main__":
    unittest.main()
