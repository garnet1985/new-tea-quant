#!/usr/bin/env python3
from pathlib import Path

from core.modules.cli.dev.scripts.py311_compat_check import collect_py311_compat_issues


def test_pep604_is_ok_on_311(tmp_path: Path):
    ok = tmp_path / "union.py"
    ok.write_text(
        "def f(x: int | None) -> str | None:\n    return x\n",
        encoding="utf-8",
    )
    issues = collect_py311_compat_issues(paths=[ok], use_py311_compile=False)
    assert not issues


def test_pep695_is_flagged(tmp_path: Path):
    bad = tmp_path / "generic.py"
    bad.write_text("class C[T]:\n    pass\n", encoding="utf-8")
    issues = collect_py311_compat_issues(paths=[bad], use_py311_compile=False)
    assert any(i.rule in {"pep695", "syntax"} for i in issues)


def test_pep604_with_future_is_ok(tmp_path: Path):
    ok = tmp_path / "ok.py"
    ok.write_text(
        "from __future__ import annotations\n\ndef f(x: int | None) -> str | None:\n    return x\n",
        encoding="utf-8",
    )
    issues = collect_py311_compat_issues(paths=[ok], use_py311_compile=False)
    assert not issues
