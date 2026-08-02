#!/usr/bin/env python3
"""对齐根目录 API.md 的契约测试。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pytest

from core.infra.update import Update
from core.infra.update.contracts import (
    PostUpgradeRunResult,
    RegisteredMigrationScript,
    RegisteredPostUpgradeAction,
)
from core.infra.update.post_upgrade.registry import clear_post_upgrade_registry

pytestmark = pytest.mark.force_run


class TestUpdateApi(unittest.TestCase):
    def test_facade_export(self):
        import core.infra.update as pkg

        self.assertEqual(pkg.__all__, ["Update"])
        self.assertTrue(hasattr(Update, "data_scripts"))
        self.assertTrue(hasattr(Update, "post_upgrade"))

    def test_data_scripts_methods(self):
        for name in ("register", "get", "list", "run"):
            self.assertTrue(callable(getattr(Update.data_scripts, name)))

    def test_post_upgrade_methods(self):
        for name in ("register", "get", "list", "run"):
            self.assertTrue(callable(getattr(Update.post_upgrade, name)))

    def test_contracts_symbols(self):
        self.assertTrue(hasattr(RegisteredMigrationScript, "__dataclass_fields__"))
        self.assertTrue(hasattr(RegisteredPostUpgradeAction, "__dataclass_fields__"))
        self.assertTrue(hasattr(PostUpgradeRunResult, "__dataclass_fields__"))

    def test_post_upgrade_run_skips_when_empty(self):
        clear_post_upgrade_registry()
        with tempfile.TemporaryDirectory() as td:
            result = Update.post_upgrade.run(Path(td))
        self.assertTrue(result.skipped)
        self.assertEqual(result.executed_count, 0)

    def test_data_scripts_register_and_get(self):
        @Update.data_scripts.register("test_api_script_xyz")
        def _fn(db, context: dict) -> None:
            return None

        entry = Update.data_scripts.get("test_api_script_xyz")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.action_id, "test_api_script_xyz")
        self.assertIn("test_api_script_xyz", Update.data_scripts.list())


if __name__ == "__main__":
    unittest.main()
