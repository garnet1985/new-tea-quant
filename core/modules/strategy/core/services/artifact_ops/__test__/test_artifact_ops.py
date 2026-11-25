"""StrategyArtifactOps scaffold smoke。"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.modules.strategy import Strategy


@pytest.fixture()
def strategies_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "strategies"
    template = root / "_template" / "empty_strategy"
    template.mkdir(parents=True)
    (template / "settings.py").write_text(
        'settings = {\n'
        '    "is_enabled": False,\n'
        '    "meta": {"key": "empty_strategy", "name": "empty"},\n'
        '}\n',
        encoding="utf-8",
    )
    (template / "strategy.py").write_text(
        "from core.modules.strategy.contracts import Records, StrategyContext, StrategyHooks\n"
        "class Empty(StrategyHooks):\n"
        "    def is_opportunity(self, ctx: StrategyContext, records: Records) -> bool:\n"
        "        return False\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "core.infra.project_context.ProjectContext.path.get_strategies_root",
        lambda: root,
    )
    return root


def test_scaffold_from_template(strategies_root: Path) -> None:
    out = Strategy.scaffold_from_template("demo/sample_v1")
    assert out.get("ok") is True, out
    dest = strategies_root / "demo" / "sample_v1"
    text = (dest / "settings.py").read_text(encoding="utf-8")
    assert '"is_enabled": True' in text
    assert '"key": "demo/sample_v1"' in text


def test_scaffold_rejects_existing(strategies_root: Path) -> None:
    assert Strategy.scaffold_from_template("demo/x").get("ok") is True
    again = Strategy.scaffold_from_template("demo/x")
    assert again.get("ok") is False
    assert "已存在" in str(again.get("error") or "")
