"""对齐 API.md 的契约测试。"""

from __future__ import annotations

import unittest

import pytest

pytestmark = pytest.mark.force_run


class TestCmdLayoutApi(unittest.TestCase):
    def test_cmd_layout_facade_exported(self) -> None:
        from core.infra.cmd_layout import CmdLayout
        import core.infra.cmd_layout as pkg

        self.assertEqual(pkg.__all__, ["CmdLayout"])
        self.assertTrue(hasattr(CmdLayout, "bar_chart"))
        self.assertTrue(hasattr(CmdLayout, "title"))
        self.assertTrue(hasattr(CmdLayout, "separator"))
        self.assertTrue(hasattr(CmdLayout, "icon"))

    def test_bar_chart_namespace_callable(self) -> None:
        from core.infra.cmd_layout import CmdLayout

        for name in ("render", "from_values", "print", "print_from_values"):
            self.assertTrue(callable(getattr(CmdLayout.bar_chart, name)))

    def test_title_namespace_callable(self) -> None:
        from core.infra.cmd_layout import CmdLayout

        for name in ("banner", "section", "print_banner", "print_section"):
            self.assertTrue(callable(getattr(CmdLayout.title, name)))

    def test_separator_namespace_callable(self) -> None:
        from core.infra.cmd_layout import CmdLayout

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

    def test_icon_namespace_callable(self) -> None:
        from core.infra.cmd_layout import CmdLayout

        for name in ("get", "i", "supports_emoji"):
            self.assertTrue(callable(getattr(CmdLayout.icon, name)))


if __name__ == "__main__":
    unittest.main()
