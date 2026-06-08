"""package_cli export/import smoke tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.infra.project_context import PathManager
from core.modules.strategy.launcher.package_cli import (
    default_export_path,
    run_strategy_bundle_export,
    run_strategy_bundle_import,
)


@pytest.fixture
def userspace_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    us = tmp_path / "userspace"
    strategy = us / "strategies" / "demo"
    strategy.mkdir(parents=True)
    (strategy / "settings.py").write_text('settings = {"name": "demo"}\n', encoding="utf-8")
    (strategy / "strategy_worker.py").write_text("class W: pass\n", encoding="utf-8")

    monkeypatch.setattr(PathManager, "userspace", staticmethod(lambda: us))
    monkeypatch.setattr(PathManager, "strategies_root", staticmethod(lambda: us / "strategies"))
    monkeypatch.setattr(PathManager, "strategy", staticmethod(lambda name: us / "strategies" / name))
    monkeypatch.setattr(PathManager, "extensions_root", staticmethod(lambda: us / "extensions"))
    monkeypatch.setattr(PathManager, "tags", staticmethod(lambda: us / "extensions" / "tags"))
    monkeypatch.setattr(
        PathManager,
        "tag_scenario",
        staticmethod(lambda name: us / "extensions" / "tags" / name),
    )
    monkeypatch.setattr(PathManager, "adapters", staticmethod(lambda: us / "extensions" / "adapters"))
    return us


def test_export_cli_writes_zip(userspace_tree: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    out = default_export_path("demo")
    code = run_strategy_bundle_export("demo", output_path=out)
    assert code == 0
    assert out.is_file()
    assert out.suffix == ".zip"


def test_import_cli_rejects_duplicate(userspace_tree: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    out = tmp_path / "demo.strategy.zip"
    assert run_strategy_bundle_export("demo", output_path=out) == 0
    assert run_strategy_bundle_import(out, force=False) == 1
