"""CHANGELOG → system.json / system.py 同步。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from devtools.quick_tools import changelog_sync as mod
from devtools.quick_tools.changelog_sync import (
    compare_system_new_features,
    parse_changelog_section,
    sync_version_metadata_from_changelog,
)


def test_parse_changelog_section_0_4_1():
    features, release_date = parse_changelog_section("0.4.1")
    assert len(features) >= 10
    assert any("单股K线" in item for item in features)
    assert release_date == "2026-06-15"


def test_parse_changelog_section_missing_version():
    with pytest.raises(ValueError, match="未找到"):
        parse_changelog_section("99.99.99")


def test_sync_writes_system_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        "\n".join(
            [
                "### v1.2.3 (2026-01-05)",
                "",
                "- feature alpha",
                "- feature beta",
                "",
                "### v1.2.2 (2025-12-01)",
                "",
                "- old",
            ]
        ),
        encoding="utf-8",
    )
    system_json = tmp_path / "system.json"
    system_json.write_text(
        json.dumps({"version": "0.0.0", "release_date": "2000-01-01", "new_features": []}),
        encoding="utf-8",
    )
    system_py = tmp_path / "system.py"
    system_py.write_text(
        "\n".join(
            [
                "_FALLBACK: Dict[str, Any] = {",
                '    "version": "0.0.0",',
                '    "release_date": "2000-01-01",',
                '    "new_features": [',
                '        "old",',
                "    ],",
                "}",
                "",
                "def _load_payload():",
                "    pass",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(mod, "CHANGELOG_PATH", changelog)
    monkeypatch.setattr(mod, "SYSTEM_JSON", system_json)
    monkeypatch.setattr(mod, "SYSTEM_PY", system_py)

    out = sync_version_metadata_from_changelog("1.2.3", release_date="2026-06-15")
    assert out == ["feature alpha", "feature beta"]

    data = json.loads(system_json.read_text(encoding="utf-8"))
    assert data["version"] == "1.2.3"
    assert data["release_date"] == "2026-01-05"
    assert data["new_features"] == out

    py_text = system_py.read_text(encoding="utf-8")
    assert '"version": "1.2.3"' in py_text
    assert '"release_date": "2026-01-05"' in py_text
    assert '"feature alpha"' in py_text
    assert '"feature beta"' in py_text
    assert "old" not in py_text


def test_compare_system_new_features_mismatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text("### v2.0.0 (TBD)\n\n- only one\n", encoding="utf-8")
    system_json = tmp_path / "system.json"
    system_json.write_text(
        json.dumps({"new_features": ["different"]}),
        encoding="utf-8",
    )
    monkeypatch.setattr(mod, "CHANGELOG_PATH", changelog)
    monkeypatch.setattr(mod, "SYSTEM_JSON", system_json)

    issues = compare_system_new_features("2.0.0")
    assert issues
    assert any("不一致" in line for line in issues)
