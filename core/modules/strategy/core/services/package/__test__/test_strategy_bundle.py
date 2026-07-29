"""Strategy share bundle resolver and round-trip tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.infra.export_import import ExportImport
from core.infra.project_context.core.path_manager import PathManager
from core.modules.strategy.core.services.package import (
    export_strategy_bundle,
    import_strategy_bundle,
    preview_strategy_bundle_import,
    resolve_strategy_bundle_specs,
)


@pytest.fixture
def userspace_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    us = tmp_path / "userspace"
    us.mkdir()

    monkeypatch.setattr(PathManager, "get_userspace_root", staticmethod(lambda: us))
    monkeypatch.setattr(PathManager, "get_strategies_root", staticmethod(lambda: us / "strategies"))
    monkeypatch.setattr(PathManager, "get_extensions_root", staticmethod(lambda: us / "extensions"))
    monkeypatch.setattr(PathManager, "get_tags_root", staticmethod(lambda: us / "extensions" / "tags"))
    monkeypatch.setattr(
        PathManager,
        "get_tag_scenario_directory",
        staticmethod(lambda name: us / "extensions" / "tags" / name),
    )
    monkeypatch.setattr(
        PathManager,
        "get_adapters_directory",
        staticmethod(lambda: us / "extensions" / "adapters"),
    )
    monkeypatch.setattr(
        PathManager,
        "get_strategy_directory",
        staticmethod(lambda name: us / "strategies" / name),
    )
    return us


def _minimal_settings(*, required=None, adapters=None) -> dict:
    return {
        "is_enabled": True,
        "meta": {"key": "demo"},
        "data": {
            "base": {"data_key": "stock.kline.daily", "params": {"adjust": "qfq"}},
            "required": list(required or []),
            "min_required_records": 30,
        },
        "goal": {},
        "simulation": {
            "execution": {
                "mode": "entity_based",
                "start_date": "20200101",
                "end_date": "20201231",
            }
        },
        "scanner": {"adapters": list(adapters or ["console"])},
    }


def _write_demo_bundle_sources(us: Path) -> None:
    strategy = us / "strategies" / "demo"
    strategy.mkdir(parents=True)
    demo_settings = _minimal_settings(
        adapters=["console", "my_webhook"],
        required=[
            {"data_key": "tag", "params": {"tag_scenario": "activity-ratio20"}},
        ],
    )
    (strategy / "settings.py").write_text(
        f"settings = {demo_settings!r}\n",
        encoding="utf-8",
    )
    (strategy / "strategy.py").write_text(
        "class DemoStrategy:\n    pass\n",
        encoding="utf-8",
    )

    tag = us / "extensions" / "tags" / "activity-ratio20"
    tag.mkdir(parents=True)
    (tag / "settings.py").write_text('Settings = {"name": "activity-ratio20"}\n', encoding="utf-8")
    (tag / "tag_worker.py").write_text("class W: pass\n", encoding="utf-8")

    adapter = us / "extensions" / "adapters" / "my_webhook"
    adapter.mkdir(parents=True)
    (adapter / "adapter.py").write_text("class A: pass\n", encoding="utf-8")


def test_resolve_includes_tag_and_adapter(userspace_tree: Path):
    _write_demo_bundle_sources(userspace_tree)
    specs = resolve_strategy_bundle_specs("demo")
    kinds = {s.kind for s in specs}
    names = {s.name for s in specs}
    assert "strategy" in kinds
    assert "tag" in kinds
    assert "adapter" in kinds
    assert "activity-ratio20" in names
    assert "my_webhook" in names
    assert "console" not in names


def test_export_import_roundtrip(userspace_tree: Path, tmp_path: Path):
    _write_demo_bundle_sources(userspace_tree)
    _manifest, blob = export_strategy_bundle("demo")

    dst = tmp_path / "dst"
    dst.mkdir()
    preview = preview_strategy_bundle_import(
        blob, userspace_root=dst, policy=ExportImport.types.ConflictPolicy.OVERWRITE
    )
    assert preview["ok"] is True
    result = import_strategy_bundle(
        blob, ExportImport.types.ConflictPolicy.OVERWRITE, userspace_root=dst
    )
    assert result.ok
    assert (dst / "strategies" / "demo" / "settings.py").is_file()
    assert (dst / "extensions" / "tags" / "activity-ratio20").is_dir()
    assert (dst / "extensions" / "adapters" / "my_webhook").is_dir()
