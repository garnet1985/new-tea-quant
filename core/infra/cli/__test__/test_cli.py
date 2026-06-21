"""Tests for CLI abbrev expansion and parser."""

from __future__ import annotations

import pytest

from core.infra.cli.abbrev import expand_argv, is_help_argv
from core.infra.cli.parser import parse_args


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ([], ["version"]),
        (["-v"], ["version"]),
        (["--version"], ["version"]),
        (["v"], ["version"]),
        (["c"], ["scan"]),
        (["sp"], ["strategy_price_factor"]),
        (["sp", "-f", "--strategy", "demo/x"], ["strategy_price_factor", "-f", "--strategy", "demo/x"]),
        (["se", "--strategy", "demo"], ["strategy_enumerate", "--strategy", "demo"]),
        (["so"], ["strategy_portfolio"]),
        (["sy"], ["strategy_analyse"]),
        (["r", "stock_klines", "-f"], ["renew", "stock_klines", "-f"]),
        (["ex", "example"], ["export_strategy", "example"]),
        (["im", "./pkg.zip"], ["import_strategy", "./pkg.zip"]),
    ],
)
def test_expand_argv(raw: list[str], expected: list[str]) -> None:
    assert expand_argv(raw) == expected


def test_parse_default_version() -> None:
    args = parse_args([])
    assert args.command == "version"


def test_parse_dash_v() -> None:
    args = parse_args(["-v"])
    assert args.command == "version"


def test_parse_sp_strategy() -> None:
    args = parse_args(["sp", "-f", "--strategy", "demo/foo"])
    assert args.command == "strategy_price_factor"
    assert args.force is True
    assert args.strategy == "demo/foo"


def test_parse_global_new_strategy() -> None:
    args = parse_args(["-n", "my_strat"])
    assert args.new_path == "my_strat"
    assert args.command is None


def test_parse_tag_new() -> None:
    args = parse_args(["t", "-n", "demo/tag"])
    assert args.command == "tag"
    assert args.new_path == "demo/tag"


def test_is_help_argv() -> None:
    assert is_help_argv(["-h"]) is True
    assert is_help_argv([]) is False
