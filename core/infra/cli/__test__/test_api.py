"""API contract tests for infra.cli Facade."""

from __future__ import annotations

import unittest

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

    def test_user_main_callable(self) -> None:
        from core.infra.cli import Cli

        self.assertTrue(callable(Cli.user.main))

    def test_user_bootstrap_callable(self) -> None:
        from core.infra.cli import Cli

        self.assertTrue(callable(Cli.user.bootstrap))

    def test_dev_main_callable(self) -> None:
        from core.infra.cli import Cli

        self.assertTrue(callable(Cli.dev.main))

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


if __name__ == "__main__":
    unittest.main()
