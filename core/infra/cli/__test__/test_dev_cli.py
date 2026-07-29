"""Tests for dev CLI abbrev expansion and parser."""

from __future__ import annotations

import pytest

from core.infra.cli.dev.abbrev import DevAbbrev
from core.infra.cli.dev.parser import parse_args

pytestmark = pytest.mark.force_run


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ([], ["version"]),
        (["-v"], ["version"]),
        (["--version"], ["version"]),
        (["ui"], ["ui"]),
        (["uk"], ["ui_kill"]),
        (["csc"], ["clear_strategy_cache"]),
        (["cgc"], ["clear_global_cache"]),
        (["ssp", "500"], ["sample_stock_pool", "500"]),
        (["p", "-core_v0.3.2"], ["pack", "--version", "0.3.2"]),
        (["pack", "--version", "1.2.3"], ["pack", "--version", "1.2.3"]),
        (["ui", "--kill-first"], ["ui", "--kill-first"]),
    ],
)
def test_expand_argv(raw: list[str], expected: list[str]) -> None:
    assert DevAbbrev.expand_argv(raw) == expected


def test_parse_default_version() -> None:
    args = parse_args([])
    assert args.command == "version"


def test_parse_dash_v() -> None:
    args = parse_args(["-v"])
    assert args.command == "version"


def test_parse_csc() -> None:
    args = parse_args(["csc"])
    assert args.command == "clear_strategy_cache"


def test_parse_pack_core_version() -> None:
    args = parse_args(["p", "-core_v0.3.2"])
    assert args.command == "pack"
    assert args.version == "0.3.2"


def test_parse_ssp_count() -> None:
    args = parse_args(["ssp", "500"])
    assert args.command == "sample_stock_pool"
    assert args.count == 500


def test_is_help_argv() -> None:
    assert DevAbbrev.is_help_argv(["-h"]) is True
    assert DevAbbrev.is_help_argv([]) is False
