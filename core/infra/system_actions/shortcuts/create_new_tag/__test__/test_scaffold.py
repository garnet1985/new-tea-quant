"""create_new_tag 单元测试。"""

from pathlib import Path

import pytest

from core.infra.system_actions.shortcuts.create_new_tag.scaffold import scaffold_tag


@pytest.fixture
def tag_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    tags = tmp_path / "extensions" / "tags"
    tag_tpl = tags / "_template" / "empty_scenario"
    tag_tpl.mkdir(parents=True)
    (tag_tpl / "settings.py").write_text('Settings = {"is_enabled": False}\n', encoding="utf-8")
    (tag_tpl / "tag_worker.py").write_text("# worker\n", encoding="utf-8")

    monkeypatch.setattr(
        "core.infra.system_actions.shortcuts.create_new_tag.scaffold.PathManager.tags",
        staticmethod(lambda: tags),
    )
    return tmp_path


def test_scaffold_tag_nested(tag_tree: Path):
    result = scaffold_tag("demo/my_tag")
    assert result.key == "demo/my_tag"
    assert (tag_tree / "extensions" / "tags" / "demo" / "my_tag" / "tag_worker.py").is_file()
