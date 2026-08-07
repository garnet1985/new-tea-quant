"""API contract tests for infra.cli Facade."""

from __future__ import annotations

import os
import unittest
from io import StringIO
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.force_run


class TestCliApi(unittest.TestCase):
    def test_cli_facade_exported(self) -> None:
        from core.infra.cli import Cli
        import core.infra.cli as pkg

        self.assertEqual(pkg.__all__, ["Cli"])
        self.assertTrue(hasattr(Cli, "user"))
        self.assertTrue(hasattr(Cli, "dev"))
        self.assertTrue(hasattr(Cli, "shared"))

    def test_user_help_returns_zero(self) -> None:
        from core.infra.cli import Cli

        buf = StringIO()
        with patch("sys.stdout", buf):
            code = Cli.user.main(["-h"])
        self.assertEqual(code, 0)
        text = buf.getvalue()
        self.assertTrue(
            "usage:" in text.lower()
            or "规则:" in text
            or "python cli.py" in text
        )

    def test_user_bootstrap_noop_when_skipped(self) -> None:
        from core.infra.cli import Cli

        env = {
            "NTQ_SKIP_AUTO_VENV": "1",
            "NTQ_SKIP_AUTO_INSTALL": "1",
        }
        with patch.dict(os.environ, env, clear=False):
            Cli.user.ensure_venv(__file__)
            Cli.user.bootstrap(__file__)

    def test_dev_help_returns_zero(self) -> None:
        from core.infra.cli import Cli

        buf = StringIO()
        with patch("sys.stdout", buf):
            code = Cli.dev.main(["-h"])
        self.assertEqual(code, 0)
        text = buf.getvalue()
        self.assertTrue(
            "usage:" in text.lower()
            or "规则:" in text
            or "python devcli.py" in text
        )

    def test_dev_version_returns_zero(self) -> None:
        from core.infra.cli import Cli

        buf = StringIO()
        with patch("sys.stdout", buf):
            code = Cli.dev.main(["version"])
        self.assertEqual(code, 0)
        self.assertIn("NTQ Core Version:", buf.getvalue())

    def test_shared_expand_argv(self) -> None:
        from core.infra.cli import Cli

        out = Cli.shared.expand_argv(
            ["sp", "-f"],
            short_to_long={"sp": "strategy_price_factor"},
            long_commands=frozenset({"strategy_price_factor"}),
        )
        self.assertEqual(out, ["strategy_price_factor", "-f"])

    def test_shared_is_help_argv(self) -> None:
        from core.infra.cli import Cli

        self.assertTrue(Cli.shared.is_help_argv(["-h"]))
        self.assertFalse(Cli.shared.is_help_argv([]))

    def test_shared_aliases_for(self) -> None:
        from core.infra.cli import Cli

        aliases = Cli.shared.aliases_for(
            {"sp": "strategy_price_factor", "spf": "strategy_price_factor"},
            "strategy_price_factor",
        )
        self.assertEqual(aliases, ["sp", "spf"])

    def test_user_default_argv_prints_help_then_version(self) -> None:
        from core.infra.cli import Cli

        buf = StringIO()
        with patch("sys.stdout", buf):
            code = Cli.user.main([])
        self.assertEqual(code, 0)
        text = buf.getvalue()
        self.assertTrue(
            "usage:" in text.lower()
            or "规则:" in text
            or "Command" in text
            or "python cli.py" in text
        )
        self.assertIn("NTQ Core Version:", text)
        help_pos = text.find("python cli.py")
        ver_pos = text.find("NTQ Core Version:")
        self.assertGreaterEqual(help_pos, 0)
        self.assertGreater(ver_pos, help_pos)

    def test_user_explicit_version_skips_help_preamble(self) -> None:
        from core.infra.cli import Cli

        buf = StringIO()
        with patch("sys.stdout", buf):
            code = Cli.user.main(["version"])
        self.assertEqual(code, 0)
        text = buf.getvalue()
        self.assertIn("NTQ Core Version:", text)
        self.assertTrue(text.strip().startswith("NTQ Core Version:"))


if __name__ == "__main__":
    unittest.main()
