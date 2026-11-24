"""lookup_framework_index + local markdown parse."""

from __future__ import annotations

import core.modules.agent.core.code.tools.general.framework_index_tool as fit
from core.modules.agent.core.code.tools.general.framework_index_lib import (
    load_local_entries,
    match_entries,
    parse_index_markdown,
)
from core.modules.agent.core.code.tools.general.framework_index_tool import (
    lookup_framework_index,
)


def test_parse_local_index_has_sharpe() -> None:
    entries = load_local_entries()
    assert entries, "framework_index.md missing or empty"
    titles = [e["title"] for e in entries]
    assert any("夏普" in t for t in titles)


def test_match_sharpe_query() -> None:
    entries = load_local_entries()
    hits = match_entries("夏普怎么算", entries, limit=3)
    assert hits
    assert "夏普" in hits[0]["title"]
    assert hits[0]["wiki"].endswith("how_sharpe_is_calculated.md")


def test_lookup_local_fallback(monkeypatch) -> None:
    monkeypatch.setattr(
        fit,
        "_try_remote",
        lambda: {"ok": False, "error": "缺少会员凭证", "reason": "missing_credential"},
    )
    out = lookup_framework_index({"query": "夏普比率如何计算"})
    assert out.get("ok") is True, out
    assert out.get("source") == "local"
    assert out.get("count", 0) >= 1
    assert "how_sharpe_is_calculated" in str(out["hits"][0].get("wiki") or "")


def test_lookup_prefers_remote(monkeypatch) -> None:
    monkeypatch.setattr(
        fit,
        "_try_remote",
        lambda: {
            "ok": True,
            "version": "remote-1",
            "entries": [
                {
                    "id": "x",
                    "title": "远端夏普条目",
                    "keywords": ["夏普", "怎么算"],
                    "wiki": "know_how/how_sharpe_is_calculated.md",
                    "module": "modules.strategy",
                    "code": ["a.py"],
                    "note": "from remote",
                }
            ],
        },
    )
    out = lookup_framework_index({"query": "夏普怎么算"})
    assert out.get("ok") is True, out
    assert out.get("source") == "remote"
    assert out.get("version") == "remote-1"
    assert out["hits"][0]["title"] == "远端夏普条目"


def test_parse_markdown_section() -> None:
    text = """---
title: t
---

# H

## Foo Bar

- keywords: a, b, c
- wiki: know_how/x.md
- module: m
- code: p1.py; p2.py
- note: hello
"""
    entries = parse_index_markdown(text)
    assert len(entries) == 1
    e = entries[0]
    assert e["title"] == "Foo Bar"
    assert e["keywords"] == ["a", "b", "c"]
    assert e["code"] == ["p1.py", "p2.py"]
