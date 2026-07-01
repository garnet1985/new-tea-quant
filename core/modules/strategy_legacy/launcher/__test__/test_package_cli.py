"""package_cli export/import smoke tests."""

from __future__ import annotations

from pathlib import Path

import pytest


from core.modules.strategy.launcher.package_cli import (
    bundle_filename,
    default_export_dir,
    default_export_path,
    parse_export_target,
    resolve_import_policy,
    run_export,
    run_strategy_bundle_export,
    run_strategy_bundle_import,
    single_entity_filename,
)
from core.infra.export_import import ExportImport
from core.infra.project_context.core.path_manager import PathManager


@pytest.fixture
def userspace_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    us = tmp_path / "userspace"
    strategy = us / "strategies" / "demo"
    strategy.mkdir(parents=True)
    (strategy / "settings.py").write_text('settings = {"name": "demo"}\n', encoding="utf-8")
    (strategy / "strategy.py").write_text(
        "\n".join(
            [
                "from core.modules.strategy.hooks import StrategyHooks",
                "class W(StrategyHooks):",
                "    def scan_opportunity(self, ctx):",
                "        return None",
                "",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(PathManager, "get_userspace_root", staticmethod(lambda: us))
    monkeypatch.setattr(PathManager, "get_strategies_root", staticmethod(lambda: us / "strategies"))
    monkeypatch.setattr(PathManager, "get_strategy_directory", staticmethod(lambda name: us / "strategies" / name))
    monkeypatch.setattr(PathManager, "get_extensions_root", staticmethod(lambda: us / "extensions"))
    monkeypatch.setattr(PathManager, "get_tags_root", staticmethod(lambda: us / "extensions" / "tags"))
    monkeypatch.setattr(
        PathManager,
        "get_tag_scenario_directory",
        staticmethod(lambda name: us / "extensions" / "tags" / name),
    )
    monkeypatch.setattr(PathManager, "get_adapters_directory", staticmethod(lambda: us / "extensions" / "adapters"))
    return us


def test_export_cli_writes_zip(userspace_tree: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    out = default_export_path("bundle", "demo")
    assert out.parent == userspace_tree
    assert out.name == bundle_filename("demo")
    code = run_strategy_bundle_export("demo", output_path=out)
    assert code == 0
    assert out.is_file()


def test_default_export_path_falls_back_to_project_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = tmp_path / "project"
    root.mkdir()
    monkeypatch.setattr(PathManager, "get_project_root", staticmethod(lambda: root))
    monkeypatch.setattr(PathManager, "get_userspace_root", staticmethod(lambda: root / "userspace"))
    assert default_export_dir() == root
    assert default_export_path("bundle", "demo") == root / "demo-strategy.zip"


def test_parse_export_target_single_tag():
    assert parse_export_target("tag:foo") == ("tag", "foo")
    assert parse_export_target("example") == ("bundle", "example")


def test_import_skip_existing_policy():
    assert resolve_import_policy(force=False, skip_existing=True) == ExportImport.types.ConflictPolicy.SKIP_EXISTING


def test_single_entity_export(userspace_tree: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    tag = userspace_tree / "extensions" / "tags" / "mytag"
    tag.mkdir(parents=True)
    (tag / "settings.py").write_text("Settings={}\n", encoding="utf-8")
    (tag / "tag_worker.py").write_text("class W: pass\n", encoding="utf-8")

    out = userspace_tree / single_entity_filename("tag", "mytag")
    assert run_export("tag:mytag", output_path=out) == 0
    assert out.is_file()


def test_import_cli_rejects_duplicate(userspace_tree: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    out = userspace_tree / bundle_filename("demo")
    assert run_strategy_bundle_export("demo", output_path=out) == 0
    assert run_strategy_bundle_import(out, force=False) == 1
