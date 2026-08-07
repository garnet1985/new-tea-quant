#!/usr/bin/env python3
"""CmdLayout.separator unit tests."""

from __future__ import annotations

import io
import unittest

import pytest

from core.infra.cmd_layout import CmdLayout
from core.infra.cmd_layout.separator.separator import Separator
from core.infra.cmd_layout.title.title import Title

pytestmark = pytest.mark.force_run


class TestSeparator(unittest.TestCase):
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
