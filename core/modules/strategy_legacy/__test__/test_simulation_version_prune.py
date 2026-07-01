#!/usr/bin/env python3
"""Simulation artifact version retention (enum / price / capital)."""

from pathlib import Path

from core.modules.strategy.services.data.output.simulation_output_retention import (
    prune_disk_output_after_sim_run,
    resolve_max_output_versions,
)
from core.modules.strategy.services.data.output.version_manager import (
    StrategyOutputVersionService,
)


def test_resolve_max_output_versions_defaults_and_reads_retention():
    assert resolve_max_output_versions({}) == 3
    assert resolve_max_output_versions(
        {"simulation": {"retention": {"max_output_versions": 5}}}
    ) == 5


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


def _isolate_sim_paths(monkeypatch, tmp_path: Path, strategy_name: str) -> None:
    

    base = tmp_path / strategy_name

    monkeypatch.setattr(
        PathManager,
        "strategy_simulation_enum",
        lambda _sn: base / "enum",
    )
    monkeypatch.setattr(
        PathManager,
        "strategy_simulation_price",
        lambda _sn: base / "price",
    )
    monkeypatch.setattr(
        PathManager,
        "strategy_simulation_capital",
        lambda _sn: base / "capital",
    )
    monkeypatch.setattr(
        "core.modules.strategy.services.data.output.simulation_output_retention.DataManager",
        lambda *a, **k: type(
            "_DM",
            (),
            {"get_table": lambda self, name: None},
        )(),
    )


def test_prune_disk_output_after_sim_run_price(tmp_path: Path, monkeypatch):
    _isolate_sim_paths(monkeypatch, tmp_path, "demo")
    root = tmp_path / "demo" / "price"
    root.mkdir(parents=True)
    for name in ("10", "11", "12"):
        (root / name).mkdir()
    prune_disk_output_after_sim_run(
        "demo",
        "price",
        {"simulation": {"retention": {"max_output_versions": 2}}},
    )
    assert sorted(p.name for p in root.iterdir() if p.is_dir()) == ["11", "12"]


def test_prune_skips_protected_dir_names(tmp_path: Path):
    root = tmp_path / "enum"
    root.mkdir()
    for name in ("1", "2", "3", "4"):
        (root / name).mkdir()
    skipped = StrategyOutputVersionService.prune_simulation_versions(
        root, 2, protected_dir_names=frozenset({"2"})
    )
    remaining = sorted(p.name for p in root.iterdir() if p.is_dir())
    assert remaining == ["2", "3", "4"]
    assert skipped == {"2"}


def test_prune_disk_output_after_sim_run_protects_path_object(tmp_path: Path, monkeypatch):
    _isolate_sim_paths(monkeypatch, tmp_path, "demo")
    root = tmp_path / "demo" / "capital"
    root.mkdir(parents=True)
    for name in ("10", "11", "12"):
        (root / name).mkdir()

    prune_disk_output_after_sim_run(
        "demo",
        "capital",
        {"simulation": {"retention": {"max_output_versions": 2}}},
        protect_output_version_dir=root / "10",
    )
    remaining = sorted(p.name for p in root.iterdir() if p.is_dir())
    assert remaining == ["10", "11", "12"]


def test_prune_disk_output_after_sim_run_protects_current_version(tmp_path: Path, monkeypatch):
    _isolate_sim_paths(monkeypatch, tmp_path, "demo")
    root = tmp_path / "demo" / "enum"
    root.mkdir(parents=True)
    for name in ("1", "2", "3", "4"):
        (root / name).mkdir()

    prune_disk_output_after_sim_run(
        "demo",
        "enum",
        {"simulation": {"retention": {"max_output_versions": 2}}},
        protect_output_version_dir="1",
    )
    remaining = sorted(p.name for p in root.iterdir() if p.is_dir())
    assert remaining == ["1", "3", "4"]


def test_prune_disk_output_after_sim_run_uses_retention_setting(tmp_path: Path, monkeypatch):
    _isolate_sim_paths(monkeypatch, tmp_path, "demo")
    root = tmp_path / "demo" / "enum"
    root.mkdir(parents=True)
    for name in ("1", "2", "3"):
        (root / name).mkdir()

    prune_disk_output_after_sim_run(
        "demo",
        "enum",
        {"simulation": {"retention": {"max_output_versions": 2}}},
    )
    assert sorted(p.name for p in root.iterdir() if p.is_dir()) == ["2", "3"]
