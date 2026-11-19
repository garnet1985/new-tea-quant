"""TagArtifactOps scaffold smoke。"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.modules.tag import Tag


@pytest.fixture()
def tags_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "tags"
    template = root / "_template" / "empty_scenario"
    template.mkdir(parents=True)
    (template / "settings.py").write_text(
        'settings = {\n'
        '    "is_enabled": False,\n'
        '    "meta": {"key": "empty_tag", "display_name": "空白"},\n'
        '    "tag_definitions": [{"name": "t1"}],\n'
        '}\n',
        encoding="utf-8",
    )
    (template / "tag.py").write_text(
        "from core.modules.tag.contracts import TagContext, TagHooks\n"
        "class Empty(TagHooks):\n"
        "    def calculate_tag(self, ctx: TagContext):\n"
        "        return None\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "core.infra.project_context.ProjectContext.path.get_tags_root",
        lambda: root,
    )
    return root


def test_scaffold_from_template_leaf_meta_key(tags_root: Path) -> None:
    out = Tag.scaffold_from_template("demo/sample_tag")
    assert out.get("ok") is True, out
    assert out.get("meta_key") == "sample_tag"
    text = (tags_root / "demo" / "sample_tag" / "settings.py").read_text(
        encoding="utf-8"
    )
    assert '"key": "sample_tag"' in text
    assert '"is_enabled": True' in text
