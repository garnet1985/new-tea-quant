#!/usr/bin/env python3
"""对齐根目录 API.md 的契约测试。"""

from __future__ import annotations

import unittest
from pathlib import Path

import pytest

from core.infra.setup import Setup
from core.infra.setup.contracts import CliInstallScope, InstallProfileName

pytestmark = pytest.mark.force_run


class TestSetupApi(unittest.TestCase):
    def test_facade_export(self):
        import core.infra.setup as pkg

        self.assertEqual(pkg.__all__, ["Setup"])
        for name in ("env", "runtime", "artifacts", "meta", "trace", "types"):
            self.assertTrue(hasattr(Setup, name))

    def test_env_methods(self):
        for name in (
            "repo_root",
            "venv_python",
            "in_virtualenv",
            "ensure_sys_path",
            "to_root_dir",
            "ensure_venv",
            "ensure_venv_for_setup_step",
            "requirements_txt",
            "ui_bff_requirements",
            "ui_fed_root",
        ):
            self.assertTrue(callable(getattr(Setup.env, name)))
        root = Setup.env.repo_root()
        self.assertIsInstance(root, Path)
        self.assertTrue((root / "core" / "system.json").is_file())
        self.assertEqual(Setup.env.ui_fed_root(), root / "core" / "ui" / "fed")

    def test_runtime_methods(self):
        for name in (
            "needs_install",
            "cli_install_scope",
            "install_cli",
            "ensure_cli_install",
            "install_ui",
            "check_ui_prerequisites",
            "launch_ui",
            "set_ui_dev_mode",
            "fed_build_ready",
            "userspace_ready",
            "mark",
        ):
            self.assertTrue(callable(getattr(Setup.runtime, name)))

    def test_artifacts_meta_trace(self):
        self.assertTrue(callable(Setup.artifacts.package_userspace))
        self.assertTrue(callable(Setup.artifacts.export_demo_data))
        self.assertTrue(callable(Setup.meta.load_step_meta))
        self.assertTrue(callable(Setup.trace.install_complete))
        self.assertTrue(callable(Setup.trace.app_start))

    def test_types(self):
        self.assertIs(Setup.types.InstallProfileName, InstallProfileName)
        self.assertIs(Setup.types.CliInstallScope, CliInstallScope)

    def test_meta_load_step_shape(self):
        steps = Setup.meta.load_step_meta(ui_only=True)
        self.assertIsInstance(steps, list)
        if steps:
            self.assertIn("id", steps[0])

    def test_cli_install_scope_value(self):
        scope = Setup.runtime.cli_install_scope()
        self.assertIn(scope, ("full", "deps_only", "none"))
