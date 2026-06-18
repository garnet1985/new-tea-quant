"""Tests for devcli abbrev expansion."""

from __future__ import annotations

import pytest

from core.infra.devcli.abbrev import expand_argv


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (["-ui"], ["ui", "run"]),
        (["-csc"], ["cache", "clear-simulation"]),
        (["-ssl", "-500"], ["pool", "sample", "500"]),
        (["-ssl", "-clear"], ["pool", "clear"]),
        (["ui", "run"], ["ui", "run"]),
    ],
)
def test_devcli_expand_argv(raw: list[str], expected: list[str]) -> None:
    assert expand_argv(raw) == expected
