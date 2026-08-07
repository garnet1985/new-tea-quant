#!/usr/bin/env python3
"""对齐根目录 API.md 的契约测试。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pytest

from core.infra.export_import import ExportImport

pytestmark = pytest.mark.force_run


def _write_artifact_tree(base: Path) -> Path:
    root = base / "strategies" / "demo"
    root.mkdir(parents=True)
    (root / "settings.py").write_text(
        'settings = {"name": "demo"}\n', encoding="utf-8"
    )
    (root / "strategy.py").write_text("class W:\n    pass\n", encoding="utf-8")
    results = root / "results" / "simulations"
    results.mkdir(parents=True)
    (results / "should_skip.txt").write_text("skip\n", encoding="utf-8")
    return root


class TestExportImportApi(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def tearDown(self) -> None:
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_facade_export(self) -> None:
        import core.infra.export_import as pkg

        self.assertEqual(pkg.__all__, ["ExportImport"])
        self.assertTrue(hasattr(ExportImport, "archive"))
        self.assertTrue(hasattr(ExportImport, "install"))
        self.assertTrue(hasattr(ExportImport, "types"))

    def test_contracts_symbols(self) -> None:
        from core.infra.export_import import contracts

        for name in (
            "ArtifactSpec",
            "ConflictPolicy",
            "BundleManifest",
            "ManifestEntry",
            "PreflightResult",
            "InstallResult",
            "ConflictItem",
            "CollectedFile",
        ):
            self.assertTrue(hasattr(contracts, name), name)
            self.assertIs(getattr(ExportImport.types, name), getattr(contracts, name))

    def test_conflict_policy_values(self) -> None:
        cp = ExportImport.types.ConflictPolicy
        self.assertEqual(cp.REJECT.value, "reject")
        self.assertEqual(cp.SKIP_EXISTING.value, "skip_existing")
        self.assertEqual(cp.OVERWRITE.value, "overwrite")

    def test_archive_install_round_trip_smoke(self) -> None:
        src = _write_artifact_tree(self.temp_path / "src_us")
        dst = self.temp_path / "dst_us"
        spec = ExportImport.types.ArtifactSpec(
            kind="strategy",
            name="demo",
            source_dir=src,
            archive_prefix="strategies/demo",
            target_relative="strategies/demo",
        )
        manifest, blob = ExportImport.archive.create(
            [spec], metadata={"bundle_type": "strategy"}
        )
        self.assertEqual(manifest.entries[0].name, "demo")
        self.assertIsInstance(blob, (bytes, bytearray))

        result = ExportImport.install.install(
            blob, dst, ExportImport.types.ConflictPolicy.REJECT
        )
        self.assertTrue(result.ok)
        self.assertTrue((dst / "strategies" / "demo" / "settings.py").is_file())
        self.assertFalse((dst / "strategies" / "demo" / "results").exists())

    def test_preflight_accepts_manifest(self) -> None:
        src = _write_artifact_tree(self.temp_path / "src_us")
        dst = self.temp_path / "dst_us"
        _write_artifact_tree(dst)
        spec = ExportImport.types.ArtifactSpec(
            kind="strategy",
            name="demo",
            source_dir=src,
            archive_prefix="strategies/demo",
            target_relative="strategies/demo",
        )
        manifest, _blob = ExportImport.archive.create([spec])
        preflight = ExportImport.install.preflight(
            manifest, dst, ExportImport.types.ConflictPolicy.REJECT
        )
        self.assertFalse(preflight.ok)
        self.assertTrue(preflight.conflicts)


if __name__ == "__main__":
    unittest.main()
