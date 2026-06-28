"""Strategy share bundle resolver and round-trip tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.infra.export_import import ExportImport
from core.infra.project_context import ProjectContext
from core.infra.project_context.core.path_manager import PathManager
from core.modules.strategy.__test__.settings_fixtures import minimal_strategy_raw
from core.modules.strategy.services.package import (
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


def _write_demo_bundle_sources(us: Path) -> None:
    strategy = us / "strategies" / "demo"
    strategy.mkdir(parents=True)
    demo_settings = minimal_strategy_raw(
        scanner={"adapters": ["console", "my_webhook"]},
        data={
            "base_required_data": {"data_id": "stock.kline.daily", "params": {"adjust": "qfq"}},
            "min_required_records": 30,
            "extra_required_data_sources": [
                {"data_id": "tag", "params": {"tag_scenario": "activity-ratio20"}},
            ],
        },
    )
    (strategy / "settings.py").write_text(
        f"settings = {demo_settings!r}\n",
        encoding="utf-8",
    )
    (strategy / "strategy_worker.py").write_text("class DemoWorker: pass\n", encoding="utf-8")

    tag = us / "extensions" / "tags" / "activity-ratio20"
    tag.mkdir(parents=True)
    (tag / "settings.py").write_text('Settings = {"name": "activity-ratio20"}\n', encoding="utf-8")
    (tag / "tag_worker.py").write_text("class TagWorker: pass\n", encoding="utf-8")

    adapter = us / "extensions" / "adapters" / "my_webhook"
    adapter.mkdir(parents=True)
    (adapter / "adapter.py").write_text("class A: pass\n", encoding="utf-8")


def test_resolve_includes_strategy_tag_and_adapter(userspace_tree: Path):
    _write_demo_bundle_sources(userspace_tree)
    specs = resolve_strategy_bundle_specs("demo")
    kinds = {s.kind for s in specs}
    assert kinds == {"strategy", "tag", "adapter"}
    names = {s.name for s in specs}
    assert names == {"demo", "activity-ratio20", "my_webhook"}


def test_export_import_round_trip(userspace_tree: Path, tmp_path: Path):
    _write_demo_bundle_sources(userspace_tree)
    dst = tmp_path / "dst_userspace"
    dst.mkdir()

    manifest, blob = export_strategy_bundle("demo")
    assert manifest.metadata.get("bundle_type") == "strategy"
    assert manifest.metadata.get("strategy_name") == "demo"
    assert isinstance(blob, (bytes, bytearray))

    result = import_strategy_bundle(blob, ExportImport.types.ConflictPolicy.REJECT, userspace_root=dst)
    assert result.ok
    assert (dst / "strategies" / "demo" / "settings.py").is_file()
    assert (dst / "extensions" / "tags" / "activity-ratio20" / "settings.py").is_file()
    assert (dst / "extensions" / "adapters" / "my_webhook" / "adapter.py").is_file()


def test_preview_reports_skip_for_existing_tag(userspace_tree: Path, tmp_path: Path):
    _write_demo_bundle_sources(userspace_tree)
    _, blob = export_strategy_bundle("demo")

    dst = tmp_path / "dst_userspace"
    _write_demo_bundle_sources(dst)

    preview = preview_strategy_bundle_import(
        blob,
        userspace_root=dst,
        policy=ExportImport.types.ConflictPolicy.SKIP_EXISTING,
    )
    assert preview["ok"] is True
    statuses = {item["kind"]: item["status"] for item in preview["items"]}
    assert statuses["tag"] == "exists_skip"
    assert statuses["strategy"] == "will_install" or statuses["strategy"] == "exists_skip"
