#!/usr/bin/env python3
from pathlib import Path

from devtools.quick_tools.py39_compat_check import collect_py39_compat_issues


def test_pep604_without_future_is_flagged(tmp_path: Path):
    bad = tmp_path / "bad.py"
    bad.write_text(
        "def f(x: int | None) -> str | None:\n    return x\n",
        encoding="utf-8",
    )
    issues = collect_py39_compat_issues(paths=[bad], use_py39_compile=False)
    assert any(i.rule == "pep604" for i in issues)


def test_pep604_with_future_is_ok(tmp_path: Path):
    ok = tmp_path / "ok.py"
    ok.write_text(
        "from __future__ import annotations\n\ndef f(x: int | None) -> str | None:\n    return x\n",
        encoding="utf-8",
    )
    issues = collect_py39_compat_issues(paths=[ok], use_py39_compile=False)
    assert not issues
