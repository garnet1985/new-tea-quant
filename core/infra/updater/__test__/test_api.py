#!/usr/bin/env python3
"""对齐根目录 API.md 的契约测试。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pytest

from core.infra.updater import Updater
from core.infra.updater.contracts import (
    PostUpgradeRunResult,
    RegisteredMigrationScript,
    RegisteredPostUpgradeAction,
)
from core.infra.updater.core.db.registry import DataScriptRegistry
from core.infra.updater.core.post_upgrade.registry import PostUpgradeRegistry

pytestmark = pytest.mark.force_run


class TestUpdateApi(unittest.TestCase):
    def tearDown(self) -> None:
        DataScriptRegistry.clear()
        PostUpgradeRegistry.clear()

    def test_facade_export(self):
        import core.infra.updater as pkg

        self.assertEqual(pkg.__all__, ["Updater"])
        self.assertTrue(hasattr(Updater, "data_scripts"))
        self.assertTrue(hasattr(Updater, "post_upgrade"))
        self.assertTrue(hasattr(Updater, "runtime"))
        self.assertTrue(hasattr(Updater, "types"))

    def test_data_scripts_methods(self):
        for name in ("register", "get", "list", "run"):
            self.assertTrue(callable(getattr(Updater.data_scripts, name)))

    def test_post_upgrade_methods(self):
        for name in ("register", "get", "list", "run"):
            self.assertTrue(callable(getattr(Updater.post_upgrade, name)))

    def test_types(self):
        self.assertIs(Updater.types.RegisteredMigrationScript, RegisteredMigrationScript)
        self.assertIs(
            Updater.types.RegisteredPostUpgradeAction, RegisteredPostUpgradeAction
        )
        self.assertIs(Updater.types.PostUpgradeRunResult, PostUpgradeRunResult)

    def test_runtime_sync_orchestrator(self):
        self.assertTrue(callable(Updater.runtime.sync_orchestrator))
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "updater"
            notes = Updater.runtime.sync_orchestrator(dest)
            self.assertTrue(notes)
            self.assertTrue((dest / "pipeline.py").is_file())
            self.assertTrue((dest / "helper.py").is_file())
            self.assertFalse((dest / "__test__").exists())

    def test_post_upgrade_run_skips_when_empty(self):
        from unittest.mock import patch

        from core.infra.updater.core.post_upgrade.runner import PostUpgradeRunner

        PostUpgradeRegistry.clear()
        with patch.object(PostUpgradeRunner, "_ensure_actions_loaded"):
            with tempfile.TemporaryDirectory() as td:
                result = Updater.post_upgrade.run(Path(td))
        self.assertTrue(result.skipped)
        self.assertEqual(result.executed_count, 0)

    def test_data_scripts_register_and_get(self):
        @Updater.data_scripts.register("test_api_script_xyz")
        def _fn(db, context: dict) -> None:
            return None

        entry = Updater.data_scripts.get("test_api_script_xyz")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.action_id, "test_api_script_xyz")
        self.assertIn("test_api_script_xyz", Updater.data_scripts.list())


if __name__ == "__main__":
    unittest.main()
