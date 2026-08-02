#!/usr/bin/env python3
"""对齐根目录 API.md 的契约测试。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pytest

from core.infra.export_import import ExportImport

pytestmark = pytest.mark.force_run


class TestExportImportApi(unittest.TestCase):
    """ExportImport API 契约测试"""

    def setUp(self):
        """创建临时测试目录"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def tearDown(self):
        """清理临时测试目录"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_export_import_facade_exists(self):
        """测试 ExportImport Facade 类存在"""
        import core.infra.export_import as pkg

        self.assertEqual(pkg.__all__, ["ExportImport"])
        self.assertIsNotNone(ExportImport)

    def test_contracts_symbols(self):
        from core.infra.export_import import contracts

        for name in (
            "ArtifactSpec",
            "ConflictPolicy",
            "BundleManifest",
            "PreflightResult",
            "InstallResult",
        ):
            self.assertTrue(hasattr(contracts, name), name)
            self.assertIs(getattr(ExportImport.types, name), getattr(contracts, name))

    def test_archive_namespace_exists(self):
        """测试 archive namespace 存在"""
        self.assertIsNotNone(ExportImport.archive)

    def test_install_namespace_exists(self):
        """测试 install namespace 存在"""
        self.assertIsNotNone(ExportImport.install)

    def test_types_namespace_exists(self):
        """测试 types namespace 存在"""
        self.assertIsNotNone(ExportImport.types)

    def test_archive_create_method_exists(self):
        """测试 archive.create 方法存在"""
        self.assertTrue(hasattr(ExportImport.archive, 'create'))

    def test_archive_extract_method_exists(self):
        """测试 archive.extract 方法存在"""
        self.assertTrue(hasattr(ExportImport.archive, 'extract'))

    def test_install_install_method_exists(self):
        """测试 install.install 方法存在"""
        self.assertTrue(hasattr(ExportImport.install, 'install'))

    def test_install_preflight_method_exists(self):
        """测试 install.preflight 方法存在"""
        self.assertTrue(hasattr(ExportImport.install, 'preflight'))

    def test_types_artifact_spec_exists(self):
        """测试 types.ArtifactSpec 类型存在"""
        self.assertTrue(hasattr(ExportImport.types, 'ArtifactSpec'))

    def test_types_conflict_policy_exists(self):
        """测试 types.ConflictPolicy 类型存在"""
        self.assertTrue(hasattr(ExportImport.types, 'ConflictPolicy'))

    def test_types_bundle_manifest_exists(self):
        """测试 types.BundleManifest 类型存在"""
        self.assertTrue(hasattr(ExportImport.types, 'BundleManifest'))

    def test_types_install_result_exists(self):
        """测试 types.InstallResult 类型存在"""
        self.assertTrue(hasattr(ExportImport.types, 'InstallResult'))

    def test_types_artifact_spec_is_class(self):
        """测试 ArtifactSpec 是类"""
        import inspect
        self.assertTrue(inspect.isclass(ExportImport.types.ArtifactSpec))

    def test_types_conflict_policy_is_enum(self):
        """测试 ConflictPolicy 是枚举"""
        import inspect
        from enum import Enum
        self.assertTrue(inspect.isclass(ExportImport.types.ConflictPolicy))
        self.assertTrue(issubclass(ExportImport.types.ConflictPolicy, Enum))


class TestArchiveApiContract(unittest.TestCase):
    """Archive namespace API 契约测试"""

    def setUp(self):
        """创建临时测试目录"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def tearDown(self):
        """清理临时测试目录"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_archive_create_api_signature(self):
        """测试 archive.create API 签名"""
        import inspect
        sig = inspect.signature(ExportImport.archive.create)
        params = list(sig.parameters.keys())

        # 必需参数：specs
        self.assertIn('specs', params)

        # 可选参数：metadata, output_path
        self.assertIn('metadata', params)
        self.assertIn('output_path', params)

    def test_archive_extract_api_signature(self):
        """测试 archive.extract API 签名"""
        import inspect
        sig = inspect.signature(ExportImport.archive.extract)
        params = list(sig.parameters.keys())

        # 必需参数：source
        self.assertIn('source', params)

        # 可选参数：dest_dir
        self.assertIn('dest_dir', params)


class TestInstallApiContract(unittest.TestCase):
    """Install namespace API 契约测试"""

    def setUp(self):
        """创建临时测试目录"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def tearDown(self):
        """清理临时测试目录"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_install_install_api_signature(self):
        """测试 install.install API 签名"""
        import inspect
        sig = inspect.signature(ExportImport.install.install)
        params = list(sig.parameters.keys())

        # 必需参数：archive, userspace_root
        self.assertIn('archive', params)
        self.assertIn('userspace_root', params)

        # 可选参数：policy
        self.assertIn('policy', params)

    def test_install_preflight_api_signature(self):
        """测试 install.preflight API 签名"""
        import inspect
        sig = inspect.signature(ExportImport.install.preflight)
        params = list(sig.parameters.keys())

        # 必需参数：extracted_root, userspace_root
        self.assertIn('extracted_root', params)
        self.assertIn('userspace_root', params)

        # 可选参数：policy
        self.assertIn('policy', params)


class TestTypesApiContract(unittest.TestCase):
    """Types namespace API 契约测试"""

    def test_artifact_spec_fields(self):
        """测试 ArtifactSpec 字段定义"""
        from dataclasses import fields
        field_names = [f.name for f in fields(ExportImport.types.ArtifactSpec)]

        # 必需字段：kind, name, source_dir, archive_prefix, target_relative
        self.assertIn('kind', field_names)
        self.assertIn('name', field_names)
        self.assertIn('source_dir', field_names)
        self.assertIn('archive_prefix', field_names)
        self.assertIn('target_relative', field_names)

    def test_conflict_policy_values(self):
        """测试 ConflictPolicy 枚举值"""
        from enum import Enum

        # 必需枚举值：REJECT, SKIP_EXISTING, OVERWRITE
        self.assertTrue(hasattr(ExportImport.types.ConflictPolicy, 'REJECT'))
        self.assertTrue(hasattr(ExportImport.types.ConflictPolicy, 'SKIP_EXISTING'))
        self.assertTrue(hasattr(ExportImport.types.ConflictPolicy, 'OVERWRITE'))

    def test_bundle_manifest_fields(self):
        """测试 BundleManifest 字段定义"""
        from dataclasses import fields
        field_names = [f.name for f in fields(ExportImport.types.BundleManifest)]

        # 必需字段：format_version, entries, exported_at, metadata
        self.assertIn('format_version', field_names)
        self.assertIn('entries', field_names)
        self.assertIn('exported_at', field_names)
        self.assertIn('metadata', field_names)

    def test_install_result_fields(self):
        """测试 InstallResult 字段定义"""
        from dataclasses import fields
        field_names = [f.name for f in fields(ExportImport.types.InstallResult)]

        # 必需字段：ok, installed, skipped, errors
        self.assertIn('ok', field_names)
        self.assertIn('installed', field_names)
        self.assertIn('skipped', field_names)
        self.assertIn('errors', field_names)


if __name__ == '__main__':
    unittest.main()