"""从模板新建策略 / Tag。"""
from __future__ import annotations

from pathlib import Path

import pytest

from core.infra.cli.user.scripts.create_from_template import CreateFromTemplate
from core.infra.project_context.core.path_manager import PathManager

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

    result = CreateFromTemplate.create_strategy("demo/sample_v1")
    assert result.kind == "strategy"
    assert result.key == "demo/sample_v1"
    assert result.dest == (strategies / "demo" / "sample_v1").resolve()
    text = (result.dest / "settings.py").read_text(encoding="utf-8")
    assert '"is_enabled": True' in text
    assert '"key": "demo/sample_v1"' in text


def test_create_tag_from_template(tmp_path: Path, monkeypatch) -> None:
    tags = tmp_path / "tags"
    _write_template(tags, Path("_template") / "empty_scenario")
    monkeypatch.setattr(PathManager, "get_tags_root", staticmethod(lambda: tags))

    result = CreateFromTemplate.create_tag("demo/sample_tag")
    assert result.kind == "tag"
    assert result.key == "demo/sample_tag"
    assert (result.dest / "settings.py").is_file()


def test_create_strategy_rejects_non_machine_readable(tmp_path: Path, monkeypatch) -> None:
    strategies = tmp_path / "strategies"
    _write_template(strategies, Path("_template") / "empty_strategy")
    monkeypatch.setattr(PathManager, "get_strategies_root", staticmethod(lambda: strategies))

    with pytest.raises(CreateFromTemplate.Error, match="machine-readable"):
        CreateFromTemplate.create_strategy("demo/市值")


def test_create_strategy_rejects_existing(tmp_path: Path, monkeypatch) -> None:
    strategies = tmp_path / "strategies"
    _write_template(strategies, Path("_template") / "empty_strategy")
    existing = strategies / "demo" / "sample_v1"
    existing.mkdir(parents=True)
    monkeypatch.setattr(PathManager, "get_strategies_root", staticmethod(lambda: strategies))

    with pytest.raises(CreateFromTemplate.Error, match="已存在"):
        CreateFromTemplate.create_strategy("demo/sample_v1")
