"""Agent rolling tools：薄封装 Strategy.write/validate_user_rolling。"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.modules.agent.core.code.tools.strategy.validate_strategy_rolling import (
    validate_strategy_rolling,
)
from core.modules.agent.core.code.tools.strategy.write_strategy_rolling import (
    write_strategy_rolling,
)


@pytest.fixture()
def strategy_folder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    folder = tmp_path / "strategies" / "roll_demo"
    folder.mkdir(parents=True)
    (folder / "settings.py").write_text(
        'settings = {"is_enabled": True, "meta": {"key": "roll_demo"}}\n',
        encoding="utf-8",
    )

    from core.modules.agent.core.code.tools.strategy import _strategy_key as key_mod
    from core.modules.strategy.core.services.artifact_ops import ops as artifact_ops

    monkeypatch.setattr(
        key_mod,
        "strategy_folder",
        lambda key: (folder, f"strategies/{key}"),
    )
    monkeypatch.setattr(
        artifact_ops.StrategyArtifactOps,
        "_folder_for_key",
        classmethod(lambda cls, key: (folder, f"strategies/{key}")),
    )
    return folder


def test_write_and_validate_rolling(strategy_folder: Path) -> None:
    body = (
        "rolling = {'windows': ["
        "{'start': '20200101', 'end': '20201231'},"
        "{'start': '20210101', 'end': '20211231'}"
        "]}\n"
    )
    written = write_strategy_rolling({"key": "roll_demo", "rolling_py": body})
    assert written.get("ok") is True, written
    assert (strategy_folder / "rolling.py").is_file()

    validated = validate_strategy_rolling({"key": "roll_demo"})
    assert validated.get("ok") is True, validated
    assert validated.get("window_count") == 2


def test_write_rolling_rejects_empty(strategy_folder: Path) -> None:
    out = write_strategy_rolling({"key": "roll_demo", "rolling_py": "   "})
    assert out.get("ok") is False
