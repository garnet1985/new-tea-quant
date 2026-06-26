#!/usr/bin/env python3
"""Strategy discovery：递归扫描与路径 ID。"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.infra.project_context import ProjectContextManager
from core.modules.strategy.__test__.settings_fixtures import minimal_strategy_raw
from core.modules.strategy.base_strategy_worker import BaseStrategyWorker
from core.modules.strategy.services.discovery import StrategyDiscoveryHelper


@pytest.fixture
def strategies_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    us = tmp_path / "userspace"
    root = us / "strategies"
    root.mkdir(parents=True)
    monkeypatch.setattr(PathManager, "userspace", staticmethod(lambda: us))
    monkeypatch.setattr(PathManager, "strategies_root", staticmethod(lambda: root))
    monkeypatch.setattr(PathManager, "strategy", staticmethod(lambda name: root / name))
    return root


def _write_strategy(folder: Path, *, key_suffix: str = "demo") -> None:
    folder.mkdir(parents=True, exist_ok=True)
    settings = minimal_strategy_raw(
        meta={"display_name": f"Display {key_suffix}", "description": "d"},
    )
    folder.joinpath("settings.py").write_text(
        f"settings = {settings!r}\n",
        encoding="utf-8",
    )
    folder.joinpath("strategy_worker.py").write_text(
        "\n".join(
            [
                "from core.modules.strategy.base_strategy_worker import BaseStrategyWorker",
                f"class Worker{key_suffix}(BaseStrategyWorker):",
                "    pass",
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_discover_nested_strategy(strategies_tree: Path):
    target = strategies_tree / "momentum" / "rsi_oversold"
    _write_strategy(target, key_suffix="Rsi")

    found = StrategyDiscoveryHelper.discover_strategies()
    assert "momentum/rsi_oversold" in found
    info = found["momentum/rsi_oversold"]
    assert info.settings.meta.display_name == "Display Rsi"
    assert info.worker_file_path.is_file()


def test_skip_non_machine_readable_path(strategies_tree: Path):
    bad = strategies_tree / "动量" / "rsi_bad"
    _write_strategy(bad, key_suffix="Bad")
    found = StrategyDiscoveryHelper.discover_strategies()
    assert "动量/rsi_bad" not in found


def test_skip_underscore_prefixed_dir(strategies_tree: Path):
    hidden = strategies_tree / "_hidden" / "demo"
    _write_strategy(hidden, key_suffix="Hidden")
    found = StrategyDiscoveryHelper.discover_strategies()
    assert not any(k.endswith("demo") for k in found if "_hidden" in k)
