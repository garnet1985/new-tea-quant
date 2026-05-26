#!/usr/bin/env python3
"""Simulation artifact version retention (enum / price / capital)."""

from pathlib import Path

from core.modules.strategy.services.data.output.version_manager import (
    StrategyOutputVersionService,
    prune_strategy_simulation_tree,
    resolve_max_output_versions,
)


def test_resolve_max_output_versions_defaults_and_reads_enumerator():
    assert resolve_max_output_versions({}) == 3
    assert resolve_max_output_versions({"enumerator": {"max_output_versions": 5}}) == 5


def test_prune_simulation_versions_keeps_newest_by_dir_name(tmp_path: Path):
    root = tmp_path / "enum"
    root.mkdir()
    for name in ("1", "2", "3", "4"):
        (root / name).mkdir()
    StrategyOutputVersionService.prune_simulation_versions(root, 3)
    remaining = sorted(p.name for p in root.iterdir() if p.is_dir())
    assert remaining == ["2", "3", "4"]


def test_prune_ignores_non_numeric_dirs(tmp_path: Path):
    root = tmp_path / "price"
    root.mkdir()
    (root / "1").mkdir()
    (root / "2").mkdir()
    (root / "latest_backup").mkdir()
    StrategyOutputVersionService.prune_simulation_versions(root, 1)
    remaining = sorted(p.name for p in root.iterdir() if p.is_dir())
    assert remaining == ["2", "latest_backup"]


def test_prune_strategy_simulation_tree_price(tmp_path: Path, monkeypatch):
    from core.infra.project_context import PathManager

    def _price_root(strategy_name: str) -> Path:
        return tmp_path / "strategies" / strategy_name / "price"

    monkeypatch.setattr(
        PathManager,
        "strategy_simulation_price",
        _price_root,
    )
    root = _price_root("demo")
    root.mkdir(parents=True)
    for name in ("10", "11", "12"):
        (root / name).mkdir()
    prune_strategy_simulation_tree(
        "demo",
        "price",
        {"enumerator": {"max_output_versions": 2}},
    )
    assert sorted(p.name for p in root.iterdir() if p.is_dir()) == ["11", "12"]
