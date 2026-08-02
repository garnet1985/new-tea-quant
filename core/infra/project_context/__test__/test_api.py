#!/usr/bin/env python3
"""对齐根目录 API.md 的契约测试。"""

from __future__ import annotations

import unittest
from pathlib import Path

import pytest

from core.infra.project_context import ProjectContext
from core.infra.project_context.contracts import (
    DEFAULT_DUCKDB_DOMAINS,
    DUCKDB_DOMAIN_FILES,
    OverridableConfigNotFoundError,
    SUPPORTED_DB_TYPES,
    merge_market_profile_dicts,
)

pytestmark = pytest.mark.force_run


class TestApi(unittest.TestCase):
    """ProjectContext API 契约测试"""

    def test_facade_export(self):
        """facade 导出 path / config / meta / cache / discovery namespace"""
        import core.infra.project_context as pkg

        self.assertEqual(pkg.__all__, ["ProjectContext"])
        self.assertTrue(hasattr(ProjectContext, "path"))
        self.assertTrue(hasattr(ProjectContext, "config"))
        self.assertTrue(hasattr(ProjectContext, "meta"))
        self.assertTrue(hasattr(ProjectContext, "cache"))
        self.assertTrue(hasattr(ProjectContext, "discovery"))

    def test_path_namespace_methods(self):
        """path namespace 包含文档化路径 API"""
        methods = [
            "get_project_root",
            "get_core_root",
            "get_userspace_root",
            "get_strategies_root",
            "get_tags_root",
            "get_strategy_directory",
            "get_tag_directory",
        ]
        for method_name in methods:
            method = getattr(ProjectContext.path, method_name)
            self.assertTrue(callable(method), f"{method_name} should be callable")

    def test_config_namespace_methods(self):
        """config namespace 包含配置加载 API"""
        methods = [
            "load_core_config",
            "load_database_config",
            "load_data_config",
            "get_default_start_date",
            "get_as_of_latest_completed_trading_date",
            "get_use_sample_stock_list",
            "merge_market_profile_dicts",
        ]
        for method_name in methods:
            method = getattr(ProjectContext.config, method_name)
            self.assertTrue(callable(method), f"{method_name} should be callable")

    def test_meta_namespace_methods(self):
        for method_name in ("core_version", "core_info"):
            self.assertTrue(callable(getattr(ProjectContext.meta, method_name)))

    def test_cache_namespace_methods(self):
        self.assertTrue(callable(ProjectContext.cache.clear_userspace_cache))

    def test_discovery_namespace_methods(self):
        for method_name in ("discover_configs", "load_overridable_config"):
            self.assertTrue(callable(getattr(ProjectContext.discovery, method_name)))

    def test_path_get_project_root(self):
        root = ProjectContext.path.get_project_root()
        self.assertIsInstance(root, Path)
        self.assertTrue(root.is_absolute())
        self.assertTrue(root.exists())

    def test_path_get_core_root(self):
        core_root = ProjectContext.path.get_core_root()
        self.assertIsInstance(core_root, Path)
        self.assertEqual(core_root.name, "core")
        self.assertTrue(core_root.exists())

    def test_path_get_userspace_root(self):
        userspace = ProjectContext.path.get_userspace_root()
        self.assertIsInstance(userspace, Path)
        self.assertTrue(userspace.is_absolute())

    def test_config_load_core_config(self):
        settings = ProjectContext.config.load_core_config("data")
        self.assertIsInstance(settings, dict)
        self.assertTrue(settings)

    def test_config_load_core_config_missing_returns_empty(self):
        settings = ProjectContext.config.load_core_config("nonexistent_core_config_xyz")
        self.assertEqual(settings, {})

    def test_config_get_default_start_date(self):
        start_date = ProjectContext.config.get_default_start_date()
        self.assertIsInstance(start_date, str)

    def test_meta_core_version(self):
        version = ProjectContext.meta.core_version()
        self.assertTrue(version is None or isinstance(version, str))

    def test_meta_core_info(self):
        info = ProjectContext.meta.core_info()
        self.assertTrue(info is None or isinstance(info, dict))

    def test_cache_clear_userspace_cache(self):
        self.assertIsNone(ProjectContext.cache.clear_userspace_cache())

    def test_discovery_discover_configs(self):
        configs = ProjectContext.discovery.discover_configs()
        self.assertIsInstance(configs, list)

    def test_discovery_load_overridable_config_success(self):
        try:
            config = ProjectContext.discovery.load_overridable_config("database", "common")
            self.assertIsInstance(config, dict)
        except OverridableConfigNotFoundError:
            pass

    def test_discovery_load_overridable_config_not_found(self):
        with self.assertRaises(OverridableConfigNotFoundError):
            ProjectContext.discovery.load_overridable_config(
                "nonexistent_domain", "nonexistent_config"
            )


class TestContracts(unittest.TestCase):
    """ProjectContext contracts 类型与常量"""

    def test_overridable_config_not_found_error(self):
        self.assertTrue(issubclass(OverridableConfigNotFoundError, FileNotFoundError))

    def test_duckdb_defaults(self):
        self.assertIn("data", DEFAULT_DUCKDB_DOMAINS)
        self.assertTrue(DUCKDB_DOMAIN_FILES)
        self.assertIn("duckdb", SUPPORTED_DB_TYPES)

    def test_merge_market_profile_dicts_callable(self):
        self.assertTrue(callable(merge_market_profile_dicts))
        self.assertTrue(callable(ProjectContext.config.merge_market_profile_dicts))


class TestEdgeCases(unittest.TestCase):
    """边界测试"""

    def test_empty_strategy_name(self):
        strategy_dir = ProjectContext.path.get_strategy_directory("")
        self.assertIsInstance(strategy_dir, Path)

    def test_empty_tag_name(self):
        tag_dir = ProjectContext.path.get_tag_directory("")
        self.assertIsInstance(tag_dir, Path)

    def test_multiple_cache_clears(self):
        ProjectContext.cache.clear_userspace_cache()
        ProjectContext.cache.clear_userspace_cache()
        userspace = ProjectContext.path.get_userspace_root()
        self.assertIsInstance(userspace, Path)


if __name__ == "__main__":
    unittest.main()
