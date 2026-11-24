"""framework_index normalize + fixture fetch."""

from __future__ import annotations

import core.modules.ntq_external.ai.framework_index as fi


def test_normalize_ok() -> None:
    out = fi.normalize_framework_index_payload(
        {
            "version": "v1",
            "entries": [
                {
                    "id": "a",
                    "title": "T",
                    "keywords": ["k1", "k2"],
                    "wiki": "w.md",
                    "code": ["a.py", "b.py"],
                }
            ],
        }
    )
    assert out["ok"] is True
    assert out["version"] == "v1"
    assert out["entries"][0]["title"] == "T"
    assert out["entries"][0]["keywords"] == ["k1", "k2"]


def test_normalize_rejects_empty_version() -> None:
    out = fi.normalize_framework_index_payload({"version": "", "entries": []})
    assert out["ok"] is False


def test_fixture_fetch(monkeypatch) -> None:
    fi.clear_framework_index_cache()
    monkeypatch.setenv(fi._FIXTURE_ENV, "1")
    out = fi.fetch_framework_index(force_refresh=True)
    assert out["ok"] is True
    assert out["version"] == "fixture-1"
    assert any("夏普" in e["title"] for e in out["entries"])


def test_missing_credential(monkeypatch) -> None:
    fi.clear_framework_index_cache()
    monkeypatch.delenv(fi._FIXTURE_ENV, raising=False)
    monkeypatch.setattr(fi, "member_token", lambda: None)
    out = fi.fetch_framework_index(force_refresh=True)
    assert out["ok"] is False
    assert out.get("reason") == "missing_credential"
