"""Tests for CLI abbrev expansion and parser."""

from __future__ import annotations

from io import StringIO
from unittest.mock import patch

import pytest

from core.infra.cli.abbrev import expand_argv, is_help_argv
from core.infra.cli.main import main
from core.infra.cli.parser import parse_args

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


def test_default_argv_prints_help_then_version() -> None:
    buf = StringIO()
    with patch("sys.stdout", buf):
        code = main([])
    assert code == 0
    text = buf.getvalue()
    assert "usage:" in text.lower() or "规则:" in text or "Command" in text or "python cli.py" in text
    assert "NTQ Core Version:" in text
    help_pos = text.find("python cli.py")
    ver_pos = text.find("NTQ Core Version:")
    assert help_pos >= 0
    assert ver_pos > help_pos


def test_explicit_version_skips_help_preamble() -> None:
    buf = StringIO()
    with patch("sys.stdout", buf):
        code = main(["version"])
    assert code == 0
    text = buf.getvalue()
    assert "NTQ Core Version:" in text
    # 显式 version 不应先整屏 dump help
    assert text.strip().startswith("NTQ Core Version:")
