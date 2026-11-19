"""Tag agent tools: create / write / validate smoke."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.modules.agent.core.code.tools.tag.create_tag import create_tag
from core.modules.agent.core.code.tools.tag.validate_tag import validate_tag
from core.modules.agent.core.code.tools.tag.write_tag_files import write_tag_files


@pytest.fixture()
def tag_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "tags"
    template = root / "_template" / "empty_scenario"
    template.mkdir(parents=True)
    (template / "settings.py").write_text(
        'settings = {\n'
        '    "is_enabled": False,\n'
        '    "meta": {"key": "empty_tag", "display_name": "空白"},\n'
        '    "data": {"base": {"data_key": "stock.kline.daily"}, "min_required_records": 0},\n'
        '    "calculation": {"update_mode": "incremental", "recompute": False,\n'
        '                    "execution": {"mode": "entity_based", "start_date": "", "end_date": ""}},\n'
        '    "tag_definitions": [{"name": "example_tag_1", "display_name": "t1"}],\n'
        '}\n',
        encoding="utf-8",
    )
    (template / "tag.py").write_text(
        "from core.modules.tag.contracts import TagContext, TagHooks\n"
        "class EmptyTagHooks(TagHooks):\n"
        "    def calculate_tag(self, ctx: TagContext):\n"
        "        return None\n",
        encoding="utf-8",
    )

    userspace_tags = tmp_path / "extensions" / "tags"
    userspace_tags.mkdir(parents=True)
    adapters = tmp_path / "extensions" / "post_process" / "adapters"
    posts = tmp_path / "extensions" / "post_process" / "post_processors"
    adapters.mkdir(parents=True)
    posts.mkdir(parents=True)
    strategies = tmp_path / "strategies"
    strategies.mkdir(parents=True)

    monkeypatch.setattr(
        "core.infra.project_context.ProjectContext.path.get_userspace_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "core.infra.project_context.ProjectContext.path.get_tags_root",
        lambda: userspace_tags,
    )
    monkeypatch.setattr(
        "core.infra.project_context.ProjectContext.path.get_strategies_root",
        lambda: strategies,
    )
    monkeypatch.setattr(
        "core.infra.project_context.ProjectContext.path.get_adapters_directory",
        lambda: adapters,
    )
    monkeypatch.setattr(
        "core.infra.project_context.ProjectContext.path.get_post_processors_directory",
        lambda: posts,
    )
    template2 = userspace_tags / "_template" / "empty_scenario"
    template2.mkdir(parents=True)
    for name in ("settings.py", "tag.py"):
        (template2 / name).write_text(
            (template / name).read_text(encoding="utf-8"), encoding="utf-8"
        )
    return userspace_tags


def test_create_write_validate_tag(tag_root: Path) -> None:
    created = create_tag({"key": "agent_smoke_tag"})
    assert created.get("ok") is True, created
    dest = tag_root / "agent_smoke_tag"
    assert (dest / "settings.py").is_file()
    text = (dest / "settings.py").read_text(encoding="utf-8")
    assert '"key": "agent_smoke_tag"' in text or "'key': 'agent_smoke_tag'" in text

    written = write_tag_files(
        {
            "key": "agent_smoke_tag",
            "tag_py": (
                "from core.modules.tag.contracts import TagContext, TagHooks\n"
                "class SmokeHooks(TagHooks):\n"
                "    def calculate_tag(self, ctx: TagContext):\n"
                "        return {\"value\": 1}\n"
            ),
            "settings_py": (
                "settings = {\n"
                '  "is_enabled": True,\n'
                '  "meta": {"key": "agent_smoke_tag", "display_name": "smoke"},\n'
                '  "data": {"base": {"data_key": "stock.kline.daily"}},\n'
                '  "calculation": {"update_mode": "incremental"},\n'
                '  "tag_definitions": [{"name": "hit", "display_name": "命中"}],\n'
                "}\n"
            ),
        }
    )
    assert written.get("ok") is True, written
    settings_text = (dest / "settings.py").read_text(encoding="utf-8")
    assert "min_required_records" in settings_text
    assert "incremental" in settings_text

    checked = validate_tag({"key": "agent_smoke_tag"})
    assert checked.get("ok") is True, checked


def test_create_tag_rejects_existing(tag_root: Path) -> None:
    assert create_tag({"key": "dup_tag"}).get("ok") is True
    again = create_tag({"key": "dup_tag"})
    assert again.get("ok") is False
    assert "已存在" in str(again.get("error") or "")
