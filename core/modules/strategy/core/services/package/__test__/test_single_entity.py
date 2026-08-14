"""Single-entity export/import tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.infra.export_import import ExportImport
from core.infra.project_context.core.path_manager import PathManager
from core.modules.strategy.core.services.package import (
    export_single_entity,
    import_strategy_bundle,
    preview_strategy_bundle_import,
)


@pytest.fixture
def userspace_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    us = tmp_path / "userspace"
    us.mkdir()
    monkeypatch.setattr(PathManager, "get_userspace_root", staticmethod(lambda: us))
    monkeypatch.setattr(PathManager, "get_strategies_root", staticmethod(lambda: us / "strategies"))
    monkeypatch.setattr(
        PathManager,
        "get_strategy_directory",
        staticmethod(lambda name: us / "strategies" / name),
    )
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
    return us


def _write_tag(us: Path, name: str = "activity-ratio20") -> None:
    tag = us / "extensions" / "tags" / name
    tag.mkdir(parents=True)
    (tag / "settings.py").write_text('Settings = {"name": "x"}\n', encoding="utf-8")
    (tag / "tag_worker.py").write_text("class W: pass\n", encoding="utf-8")


def test_export_single_tag(userspace_tree: Path):
    _write_tag(userspace_tree)
    manifest, blob = export_single_entity("tag", "activity-ratio20")
    assert manifest.metadata.get("scope") == "single"
    assert manifest.metadata.get("bundle_type") == "tag"
    assert len(manifest.entries) == 1
    assert manifest.entries[0].kind == "tag"


def test_single_tag_import_rejects_duplicate(userspace_tree: Path, tmp_path: Path):
    _write_tag(userspace_tree)
    _, blob = export_single_entity("tag", "activity-ratio20")

    dst = tmp_path / "dst"
    _write_tag(dst)

    preview = preview_strategy_bundle_import(
        blob, userspace_root=dst, policy=ExportImport.types.ConflictPolicy.REJECT
    )
    assert preview["ok"] is False
    result = import_strategy_bundle(
        blob, ExportImport.types.ConflictPolicy.REJECT, userspace_root=dst
    )
    assert not result.ok
