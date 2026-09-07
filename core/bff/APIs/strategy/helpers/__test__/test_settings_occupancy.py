"""Tests for settings.py occupancy (rev + execute projection)."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.bff.APIs.strategy.helpers.settings_occupancy import (
    SettingsFileConflict,
    SettingsOccupancy,
)


def _write_settings(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")


def test_file_rev_changes_with_bytes(tmp_path: Path):
    settings_file = tmp_path / "settings.py"
    _write_settings(settings_file, "settings = {'a': 1}\n")
    first = SettingsOccupancy.file_rev(settings_file)
    assert first
    _write_settings(settings_file, "settings = {'a': 2}\n")
    assert SettingsOccupancy.file_rev(settings_file) != first


def test_file_rev_missing_is_empty(tmp_path: Path):
    assert SettingsOccupancy.file_rev(tmp_path / "missing.py") == ""


def test_occupancy_from_path_loads_disk_settings(tmp_path: Path):
    settings_file = tmp_path / "settings.py"
    _write_settings(
        settings_file,
        "settings = {'is_enabled': True, 'meta': {'key': 'demo'}}\n",
    )
    occupancy = SettingsOccupancy.occupancy_from_path(settings_file)
    assert occupancy["settings_rev"]
    assert occupancy["disk_settings"]["meta"]["key"] == "demo"
    assert occupancy["disk_settings"]["is_enabled"] is True
    # 稀疏文件也会投影出默认值；这里只保证能抽出 dict
    assert isinstance(occupancy["execute_settings"], dict)


def test_require_match_raises_on_mismatch(tmp_path: Path, monkeypatch):
    settings_file = tmp_path / "settings.py"
    _write_settings(settings_file, "settings = {'x': 1}\n")
    monkeypatch.setattr(
        SettingsOccupancy, "settings_path", classmethod(lambda cls, _n: settings_file)
    )
    with pytest.raises(SettingsFileConflict) as exc:
        SettingsOccupancy.require_match("demo", "stale-rev")
    assert exc.value.occupancy["disk_settings"]["x"] == 1


def test_require_match_force_skips(tmp_path: Path, monkeypatch):
    settings_file = tmp_path / "settings.py"
    _write_settings(settings_file, "settings = {'x': 1}\n")
    monkeypatch.setattr(
        SettingsOccupancy, "settings_path", classmethod(lambda cls, _n: settings_file)
    )
    occupancy = SettingsOccupancy.require_match("demo", "stale-rev", force=True)
    assert occupancy["disk_settings"]["x"] == 1


def test_require_match_none_skips(tmp_path: Path, monkeypatch):
    settings_file = tmp_path / "settings.py"
    _write_settings(settings_file, "settings = {'x': 1}\n")
    monkeypatch.setattr(
        SettingsOccupancy, "settings_path", classmethod(lambda cls, _n: settings_file)
    )
    occupancy = SettingsOccupancy.require_match("demo", None)
    assert occupancy["settings_rev"]


def test_parse_if_match_strips_quotes():
    assert SettingsOccupancy.parse_if_match('"abc"') == "abc"
    assert SettingsOccupancy.parse_if_match("W/\"abc\"") == "abc"
    assert SettingsOccupancy.parse_if_match("abc") == "abc"


def test_expected_rev_prefers_if_match():
    assert (
        SettingsOccupancy.expected_rev_from_request(
            {"settings_rev": "body"},
            if_match_header='"header"',
        )
        == "header"
    )
    assert (
        SettingsOccupancy.expected_rev_from_request({"settings_rev": "body"})
        == "body"
    )
    assert SettingsOccupancy.expected_rev_from_request({}) is None
