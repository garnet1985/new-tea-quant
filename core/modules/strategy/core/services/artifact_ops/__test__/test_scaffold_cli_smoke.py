"""Strategy/Tag.scaffold_from_template 冒烟（原 CLI 脚手架用例）。"""
from __future__ import annotations

from pathlib import Path

import pytest

from core.infra.project_context.core.path_manager import PathManager
from core.modules.strategy import Strategy
from core.modules.tag import Tag

pytestmark = pytest.mark.force_run

_SETTINGS = '''
SETTINGS = {
    "is_enabled": False,
    "meta": {
        "name": "empty",
    },
}
'''


def _write_template(root: Path, rel: Path) -> None:
    dest = root / rel
    dest.mkdir(parents=True)
    (dest / "settings.py").write_text(_SETTINGS, encoding="utf-8")


def test_create_strategy_from_template(tmp_path: Path, monkeypatch) -> None:
    strategies = tmp_path / "strategies"
    _write_template(strategies, Path("_template") / "empty_strategy")
    monkeypatch.setattr(PathManager, "get_strategies_root", staticmethod(lambda: strategies))

    out = Strategy.scaffold_from_template("demo/sample_v1")
    assert out.get("ok") is True
    assert out.get("key") == "demo/sample_v1"
    dest = Path(str(out["dest"]))
    assert dest == (strategies / "demo" / "sample_v1").resolve()
    text = (dest / "settings.py").read_text(encoding="utf-8")
    assert '"is_enabled": True' in text
    assert '"key": "demo/sample_v1"' in text


def test_create_tag_from_template(tmp_path: Path, monkeypatch) -> None:
    tags = tmp_path / "tags"
    _write_template(tags, Path("_template") / "empty_scenario")
    monkeypatch.setattr(PathManager, "get_tags_root", staticmethod(lambda: tags))

    out = Tag.scaffold_from_template("demo/sample_tag")
    assert out.get("ok") is True
    assert out.get("key") == "demo/sample_tag"
    assert (Path(str(out["dest"])) / "settings.py").is_file()


def test_create_strategy_rejects_non_machine_readable(tmp_path: Path, monkeypatch) -> None:
    strategies = tmp_path / "strategies"
    _write_template(strategies, Path("_template") / "empty_strategy")
    monkeypatch.setattr(PathManager, "get_strategies_root", staticmethod(lambda: strategies))

    out = Strategy.scaffold_from_template("demo/市值")
    assert out.get("ok") is False
    assert "machine-readable" in str(out.get("error") or "")


def test_create_strategy_rejects_existing(tmp_path: Path, monkeypatch) -> None:
    strategies = tmp_path / "strategies"
    _write_template(strategies, Path("_template") / "empty_strategy")
    existing = strategies / "demo" / "sample_v1"
    existing.mkdir(parents=True)
    monkeypatch.setattr(PathManager, "get_strategies_root", staticmethod(lambda: strategies))

    out = Strategy.scaffold_from_template("demo/sample_v1")
    assert out.get("ok") is False
    assert "已存在" in str(out.get("error") or "")
