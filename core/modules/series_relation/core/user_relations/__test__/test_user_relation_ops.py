"""UserSeriesRelationOps：scaffold + write + validate。"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.modules.series_relation import SeriesRelation


@pytest.fixture()
def relations_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "extensions" / "series_relation"
    template = root / "_template" / "empty_relation"
    template.mkdir(parents=True)
    (template / "settings.py").write_text(
        "settings = {\n"
        '    "meta": {"key": "empty_relation", "display_name": "空"},\n'
        '    "series": [\n'
        '        {"data_key": "macro.lpr", "field": "lpr_1_y", "label": "A"},\n'
        '        {"data_key": "macro.lpr", "field": "lpr_5_y", "label": "B"},\n'
        "    ],\n"
        '    "range": {"start_date": "", "end_date": ""},\n'
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


def test_scaffold_user_series_relation(relations_root: Path) -> None:
    out = SeriesRelation.scaffold_user_series_relation(
        key="my_compare", display_name="我的对比"
    )
    assert out.get("ok") is True, out
    text = (relations_root / "my_compare" / "settings.py").read_text(encoding="utf-8")
    assert '"key": "my_compare"' in text
    assert "我的对比" in text


def test_write_and_validate(relations_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert SeriesRelation.scaffold_user_series_relation(key="pair").get("ok") is True

    # 校验时跳过契约声明查找（测试不依赖真实 ContractIssuer）
    monkeypatch.setattr(
        SeriesRelation,
        "_declaration_lookup",
        staticmethod(lambda: (lambda _k: {
            "meta": {"type": "time_series", "scope": "global"},
        })),
    )

    body = (
        "settings = {\n"
        '  "meta": {"key": "wrong", "display_name": "Pair"},\n'
        '  "series": [\n'
        '    {"data_key": "macro.lpr", "field": "lpr_1_y", "label": "LPR1"},\n'
        '    {"data_key": "macro.lpr", "field": "lpr_5_y", "label": "LPR5"},\n'
        "  ],\n"
        '  "range": {"start_date": "", "end_date": ""},\n'
        '  "normalize": "zscore",\n'
        '  "fill": "none",\n'
        '  "analyze": False,\n'
        "}\n"
    )
    written = SeriesRelation.write_user_series_relation_settings(
        key="pair", settings_py=body
    )
    assert written.get("ok") is True, written
    text = (relations_root / "pair" / "settings.py").read_text(encoding="utf-8")
    assert "pair" in text  # meta.key forced

    checked = SeriesRelation.validate_user_series_relation(key="pair")
    assert checked.get("ok") is True, checked
    assert checked.get("series_count") == 2
