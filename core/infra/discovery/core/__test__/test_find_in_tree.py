"""FileUtils.find_in_tree / Discovery.file.find_in_tree 行为单测。"""
from __future__ import annotations

from pathlib import Path

import pytest

from core.infra.discovery import Discovery

pytestmark = pytest.mark.force_run


def test_find_in_tree_direct(tmp_path: Path) -> None:
    target = tmp_path / "kline_daily" / "config.py"
    target.parent.mkdir()
    target.write_text("CONFIG = {}\n", encoding="utf-8")
    found = Discovery.file.find_in_tree(tmp_path, "kline_daily", "config.py")
    assert found == target.resolve()


def test_find_in_tree_nested(tmp_path: Path) -> None:
    target = tmp_path / "stock" / "klines" / "kline_daily" / "config.py"
    target.parent.mkdir(parents=True)
    target.write_text("CONFIG = {}\n", encoding="utf-8")
    found = Discovery.file.find_in_tree(tmp_path, "kline_daily", "config.py")
    assert found == target.resolve()


def test_find_in_tree_prefers_direct_over_nested(tmp_path: Path) -> None:
    direct = tmp_path / "demo" / "config.py"
    nested = tmp_path / "group" / "demo" / "config.py"
    direct.parent.mkdir()
    nested.parent.mkdir(parents=True)
    direct.write_text("direct\n", encoding="utf-8")
    nested.write_text("nested\n", encoding="utf-8")
    found = Discovery.file.find_in_tree(tmp_path, "demo", "config.py")
    assert found == direct.resolve()


def test_find_in_tree_missing(tmp_path: Path) -> None:
    assert Discovery.file.find_in_tree(tmp_path, "missing", "config.py") is None


def test_find_in_tree_rejects_bad_key(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        Discovery.file.find_in_tree(tmp_path, "../x", "config.py")
    with pytest.raises(ValueError):
        Discovery.file.find_in_tree(tmp_path, "a/b", "config.py")
