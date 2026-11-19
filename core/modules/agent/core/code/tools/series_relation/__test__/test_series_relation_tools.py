"""Agent series_relation tools：薄封装。"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.modules.agent.core.code.tools.series_relation.create_series_relation import (
    create_series_relation,
)


@pytest.fixture()
def relations_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "extensions" / "series_relation"
    template = root / "_template" / "empty_relation"
    template.mkdir(parents=True)
    (template / "settings.py").write_text(
        "settings = {\n"
        '    "meta": {"key": "empty_relation", "display_name": "空"},\n'
        '    "series": [\n'
        '        {"data_key": "macro.lpr", "field": "lpr_1_y"},\n'
        '        {"data_key": "macro.lpr", "field": "lpr_5_y"},\n'
        "    ],\n"
        '    "normalize": "zscore",\n'
        '    "fill": "none",\n'
        '    "analyze": True,\n'
        "}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "core.infra.project_context.ProjectContext.path.get_series_relation_root",
        lambda: root,
    )
    return root


def test_agent_create_series_relation(relations_root: Path) -> None:
    created = create_series_relation({"key": "agent_rel"})
    assert created.get("ok") is True, created
    assert (relations_root / "agent_rel" / "settings.py").is_file()
