"""infra.export_import round-trip and conflict policy tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.infra.export_import import ExportImport

pytestmark = pytest.mark.force_run


def _write_strategy_tree(base: Path) -> Path:
    strategy_dir = base / "strategies" / "demo"
    strategy_dir.mkdir(parents=True)
    (strategy_dir / "settings.py").write_text('settings = {"name": "demo"}\n', encoding="utf-8")
    (strategy_dir / "strategy.py").write_text(
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
    results = strategy_dir / "results" / "simulations"
    results.mkdir(parents=True)
    (results / "should_skip.txt").write_text("skip me\n", encoding="utf-8")
    return strategy_dir


def test_create_and_install_round_trip(tmp_path: Path):
    src_us = tmp_path / "src_userspace"
    dst_us = tmp_path / "dst_userspace"
    strategy_dir = _write_strategy_tree(src_us)

    spec = ExportImport.types.ArtifactSpec(
        kind="strategy",
        name="demo",
        source_dir=strategy_dir,
        archive_prefix="strategies/demo",
        target_relative="strategies/demo",
    )
    manifest, blob = ExportImport.archive.create([spec], metadata={"bundle_type": "strategy"})
    assert manifest.entries[0].name == "demo"
    assert isinstance(blob, (bytes, bytearray))

    result = ExportImport.install.install(blob, dst_us, ExportImport.types.ConflictPolicy.REJECT)
    assert result.ok
    assert (dst_us / "strategies" / "demo" / "settings.py").is_file()
    assert not (dst_us / "strategies" / "demo" / "results").exists()


def test_preflight_reject_when_target_exists(tmp_path: Path):
    src_us = tmp_path / "src_userspace"
    dst_us = tmp_path / "dst_userspace"
    strategy_dir = _write_strategy_tree(src_us)
    _write_strategy_tree(dst_us)

    spec = ExportImport.types.ArtifactSpec(
        kind="strategy",
        name="demo",
        source_dir=strategy_dir,
        archive_prefix="strategies/demo",
        target_relative="strategies/demo",
    )
    manifest, blob = ExportImport.archive.create([spec])

    # Extract blob to temp dir for preflight
    extracted_root, _ = ExportImport.archive.extract(blob)
    preflight = ExportImport.install.preflight(extracted_root, dst_us, ExportImport.types.ConflictPolicy.REJECT)
    assert not preflight.ok
    assert preflight.conflicts

    result = ExportImport.install.install(blob, dst_us, ExportImport.types.ConflictPolicy.REJECT)
    assert not result.ok


def test_skip_existing_leaves_destination_unchanged(tmp_path: Path):
    src_us = tmp_path / "src_userspace"
    dst_us = tmp_path / "dst_userspace"
    strategy_dir = _write_strategy_tree(src_us)
    existing = _write_strategy_tree(dst_us)
    (existing / "settings.py").write_text('settings = {"name": "old"}\n', encoding="utf-8")

    spec = ExportImport.types.ArtifactSpec(
        kind="strategy",
        name="demo",
        source_dir=strategy_dir,
        archive_prefix="strategies/demo",
        target_relative="strategies/demo",
    )
    _, blob = ExportImport.archive.create([spec])

    result = ExportImport.install.install(blob, dst_us, ExportImport.types.ConflictPolicy.SKIP_EXISTING)
    assert result.ok
    assert result.skipped
    assert 'old' in (dst_us / "strategies" / "demo" / "settings.py").read_text(encoding="utf-8")


def test_overwrite_replaces_existing_tree(tmp_path: Path):
    src_us = tmp_path / "src_userspace"
    dst_us = tmp_path / "dst_userspace"
    strategy_dir = _write_strategy_tree(src_us)
    existing = _write_strategy_tree(dst_us)
    (existing / "settings.py").write_text('settings = {"name": "old"}\n', encoding="utf-8")

    spec = ExportImport.types.ArtifactSpec(
        kind="strategy",
        name="demo",
        source_dir=strategy_dir,
        archive_prefix="strategies/demo",
        target_relative="strategies/demo",
    )
    _, blob = ExportImport.archive.create([spec])

    result = ExportImport.install.install(blob, dst_us, ExportImport.types.ConflictPolicy.OVERWRITE)
    assert result.ok
    assert '"name": "demo"' in (dst_us / "strategies" / "demo" / "settings.py").read_text(encoding="utf-8")
