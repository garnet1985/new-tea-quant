"""create_new_strategy 单元测试。"""

from pathlib import Path

import pytest

from core.infra.system_actions.shortcuts._shared import ScaffoldError
from core.infra.system_actions.shortcuts.create_new_strategy.scaffold import scaffold_strategy


@pytest.fixture
def strategy_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    strategies = tmp_path / "strategies"
    strategy_tpl = strategies / "_template" / "empty_strategy"
    strategy_tpl.mkdir(parents=True)
    (strategy_tpl / "settings.py").write_text('settings = {"is_enabled": False}\n', encoding="utf-8")
    (strategy_tpl / "strategy_worker.py").write_text("# worker\n", encoding="utf-8")

    monkeypatch.setattr(
        "core.infra.system_actions.shortcuts.create_new_strategy.scaffold.PathManager.strategies_root",
        staticmethod(lambda: strategies),
    )
    return tmp_path


def test_scaffold_strategy(strategy_tree: Path):
    result = scaffold_strategy("my_alpha")
    assert result.key == "my_alpha"
    dest = strategy_tree / "strategies" / "my_alpha"
    assert dest.is_dir()
    assert (dest / "strategy_worker.py").is_file()
    assert '"is_enabled": True' in (dest / "settings.py").read_text(encoding="utf-8")


def test_scaffold_rejects_existing(strategy_tree: Path):
    scaffold_strategy("dup")
    with pytest.raises(ScaffoldError, match="目标已存在"):
        scaffold_strategy("dup")


def test_scaffold_rejects_bad_segment(strategy_tree: Path):
    with pytest.raises(ScaffoldError, match="machine-readable"):
        scaffold_strategy("_bad")
