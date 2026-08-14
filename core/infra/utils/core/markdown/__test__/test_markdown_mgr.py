"""Tests for MarkdownMgr ({{:token}} template fill)."""
from __future__ import annotations

from pathlib import Path

import pytest

from core.infra.utils.core.markdown import MarkdownMgr

pytestmark = pytest.mark.force_run


def test_extract_tokens_ordered_unique():
    text = "A {{:name}} B {{:wall_clock_seconds}} C {{:name}}"
    assert MarkdownMgr.extract_tokens(text) == ["name", "wall_clock_seconds"]


def test_plain_double_brace_not_token():
    text = "keep {{name}} and fill {{:name}}"
    assert MarkdownMgr.extract_tokens(text) == ["name"]


def test_load_template_fill_save(tmp_path: Path):
    tpl = tmp_path / "t.md"
    tpl.write_text("# {{:title}}\n\ntime={{:wall_clock_seconds}}\n", encoding="utf-8")
    mgr = MarkdownMgr.load_template(tpl)
    assert mgr.tokens == ["title", "wall_clock_seconds"]
    mgr.fill("title", "Report")
    mgr.fill("wall_clock_seconds", "3s")
    out = tmp_path / "out" / "REPORT.md"
    path = mgr.save(out)
    assert path.is_file()
    body = path.read_text(encoding="utf-8")
    assert body == "# Report\n\ntime=3s\n"
    assert "{{:" not in body


def test_fill_overwrite_and_normalize():
    mgr = MarkdownMgr.from_text("x={{:n}}")
    mgr.fill("n", "a")
    mgr.fill("n", "b")
    assert mgr.values["n"] == "b"
    mgr.fill("n", None)
    assert mgr.values["n"] == ""
    mgr.fill("n", 123)
    assert mgr.values["n"] == ""
    mgr.fill("{{:n}}", "ok")
    assert mgr.render() == "x=ok"


def test_save_missing_token_raises(tmp_path: Path):
    mgr = MarkdownMgr.from_text("{{:a}} {{:b}}")
    mgr.fill("a", "1")
    with pytest.raises(ValueError, match="未填 token"):
        mgr.render()
    mgr.fill("b", "")
    assert mgr.render() == "1 "


def test_clear_resets_values_not_template():
    mgr = MarkdownMgr.from_text("{{:a}}")
    mgr.fill("a", "1")
    mgr.clear()
    assert mgr.values == {}
    assert mgr.tokens == ["a"]
    with pytest.raises(ValueError):
        mgr.render()


def test_fill_many():
    mgr = MarkdownMgr.from_text("{{:a}}-{{:b}}")
    mgr.fill_many({"a": "x", "b": "y"})
    assert mgr.render() == "x-y"
