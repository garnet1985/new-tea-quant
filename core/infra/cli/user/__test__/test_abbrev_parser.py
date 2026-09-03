"""Unit tests for user CLI abbrev expansion and parser."""

from __future__ import annotations

import pytest

from core.infra.cli.user.abbrev import UserAbbrev
from core.infra.cli.user.parser import UserParser

pytestmark = pytest.mark.force_run


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ([], ["version"]),
        (["-v"], ["version"]),
        (["--version"], ["version"]),
        (["v"], ["version"]),
        (["c"], ["scan"]),
        (["sp"], ["strategy_price_factor"]),
        (
            ["sp", "-f", "--strategy", "demo/x"],
            ["strategy_price_factor", "-f", "--strategy", "demo/x"],
        ),
        (["se", "--strategy", "demo"], ["strategy_enumerate", "--strategy", "demo"]),
        (["so"], ["strategy_portfolio"]),
        (["sdv", "--strategy", "rsi_v1:3"], ["strategy_delete_version", "--strategy", "rsi_v1:3"]),
        (["r", "stock_klines", "-f"], ["renew", "stock_klines", "-f"]),
        (["ex", "example"], ["export_strategy", "example"]),
        (["im", "./pkg.zip"], ["import_strategy", "./pkg.zip"]),
        (["id"], ["import_data"]),
        (["id", "-f"], ["import_data", "-f"]),
    ],
)
def test_expand_argv(raw: list[str], expected: list[str]) -> None:
    assert UserAbbrev.expand_argv(raw) == expected


def test_parse_default_version() -> None:
    args = UserParser.parse_args([])
    assert args.command == "version"


def test_parse_dash_v() -> None:
    args = UserParser.parse_args(["-v"])
    assert args.command == "version"


def test_parse_sp_strategy() -> None:
    args = UserParser.parse_args(["sp", "-f", "--strategy", "demo/foo"])
    assert args.command == "strategy_price_factor"
    assert args.force is True
    assert args.strategy == "demo/foo"


def test_parse_global_new_strategy() -> None:
    args = UserParser.parse_args(["-n", "my_strat"])
    assert args.new_path == "my_strat"
    assert args.command is None


def test_parse_tag_new() -> None:
    args = UserParser.parse_args(["t", "-n", "demo/tag"])
    assert args.command == "tag"
    assert args.new_path == "demo/tag"


def test_parse_tag_list_and_dry_run() -> None:
    args = UserParser.parse_args(["tag", "--list", "--dry-run", "--entity-limit", "10"])
    assert args.command == "tag"
    assert args.list is True
    assert args.dry_run is True
    assert args.entity_limit == 10


def test_parse_sdv_strategy_version() -> None:
    args = UserParser.parse_args(["sdv", "--strategy", "rsi_v1:3"])
    assert args.command == "strategy_delete_version"
    assert args.strategy == "rsi_v1:3"


def test_parse_sdv_requires_strategy() -> None:
    with pytest.raises(SystemExit):
        UserParser.parse_args(["sdv"])


def test_parse_strategy_version_spec() -> None:
    from core.infra.cli.user.handlers import UserHandlers

    assert UserHandlers.parse_strategy_version_spec("rsi_v1:3") == ("rsi_v1", 3)
    assert UserHandlers.parse_strategy_version_spec("rsi_v1:v3") == ("rsi_v1", 3)
    assert UserHandlers.parse_strategy_version_spec("demo/foo:v6") == ("demo/foo", 6)
    with pytest.raises(ValueError, match="策略:版本"):
        UserHandlers.parse_strategy_version_spec("rsi_v1")
    with pytest.raises(ValueError, match="策略:版本"):
        UserHandlers.parse_strategy_version_spec("rsi_v1:0")
    with pytest.raises(ValueError, match="策略:版本"):
        UserHandlers.parse_strategy_version_spec(":3")


def test_is_help_argv() -> None:
    assert UserAbbrev.is_help_argv(["-h"]) is True
    assert UserAbbrev.is_help_argv([]) is False


def test_run_strategy_delete_version_ok(monkeypatch, capsys) -> None:
    from argparse import Namespace

    from core.infra.cli.user.handlers import UserHandlers

    class FakeStrategy:
        @staticmethod
        def resolve(spec: str) -> str:
            assert spec == "rsi_v1"
            return "rsi_v1"

        @staticmethod
        def delete_simulation_version(key: str, sid: int) -> dict:
            assert key == "rsi_v1"
            assert sid == 3
            return {"ok": True, "deleted": True, "version_id": "v3"}

    monkeypatch.setattr("core.modules.strategy.Strategy", FakeStrategy)
    UserHandlers._run_strategy_delete_version(Namespace(strategy="rsi_v1:3"))
    assert "已删除 rsi_v1 v3" in capsys.readouterr().out


def test_run_strategy_delete_version_missing_strategy(monkeypatch) -> None:
    from argparse import Namespace

    from core.infra.cli.user.handlers import UserHandlers

    class FakeStrategy:
        @staticmethod
        def resolve(spec: str) -> str:
            raise FileNotFoundError(spec)

    monkeypatch.setattr("core.modules.strategy.Strategy", FakeStrategy)
    with pytest.raises(SystemExit):
        UserHandlers._run_strategy_delete_version(Namespace(strategy="nope:3"))
