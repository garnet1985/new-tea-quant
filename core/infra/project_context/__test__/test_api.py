#!/usr/bin/env python3
"""Project Context API contract tests.

遵循 CORE_MODULE_STANDARDS.md 规范：
- test_cases.yaml 定义测试注册表
- 覆盖 api.yaml 中定义的稳定 API
- 分组测试、契约验证、边界测试
"""

from __future__ import annotations

import unittest
from pathlib import Path
from typing import Optional, Dict, Any

from core.infra.project_context import ProjectContext
from core.infra.project_context.contracts import OverridableConfigNotFoundError


class TestApi(unittest.TestCase):
    """ProjectContext API 契约测试"""

    def test_facade_export(self):
        """facade 导出 path / config / meta / cache / discovery namespace"""
        # 验证 namespace 存在
        self.assertTrue(hasattr(ProjectContext, 'path'))
        self.assertTrue(hasattr(ProjectContext, 'config'))
        self.assertTrue(hasattr(ProjectContext, 'meta'))
        self.assertTrue(hasattr(ProjectContext, 'cache'))
        self.assertTrue(hasattr(ProjectContext, 'discovery'))

    def test_path_namespace_methods(self):
        """path namespace 包含所有路径 API"""
        methods = [
            'get_project_root',
            'get_core_root',
            'get_userspace_root',
            'get_strategies_root',
            'get_tags_root',
            'get_strategy_directory',
            'get_tag_directory',
        ]
        for method_name in methods:
            method = getattr(ProjectContext.path, method_name)
            self.assertTrue(callable(method), f"{method_name} should be callable")

    def test_config_namespace_methods(self):
        """config namespace 包含配置加载 API"""
        methods = [
            'load_core_config',
            'load_database_config',
            'load_data_config',
            'get_default_start_date',
            'get_as_of_latest_completed_trading_date',
            'get_use_sample_stock_list',
        ]
        for method_name in methods:
            method = getattr(ProjectContext.config, method_name)
            self.assertTrue(callable(method), f"{method_name} should be callable")

    def test_meta_namespace_methods(self):
        """meta namespace 包含元数据 API"""
        methods = [
            'core_version',
            'core_info',
        ]
        for method_name in methods:
            method = getattr(ProjectContext.meta, method_name)
            self.assertTrue(callable(method), f"{method_name} should be callable")

    def test_cache_namespace_methods(self):
        """cache namespace 包含缓存管理 API"""
        methods = [
            'clear_userspace_cache',
        ]
        for method_name in methods:
            method = getattr(ProjectContext.cache, method_name)
            self.assertTrue(callable(method), f"{method_name} should be callable")

    def test_discovery_namespace_methods(self):
        """discovery namespace 包含配置发现 API"""
        methods = [
            'discover_configs',
            'load_overridable_config',
        ]
        for method_name in methods:
            method = getattr(ProjectContext.discovery, method_name)
            self.assertTrue(callable(method), f"{method_name} should be callable")

    def test_path_get_project_root(self):
        """get_project_root 返回有效项目根目录"""
        root = ProjectContext.path.get_project_root()
        self.assertIsInstance(root, Path)
        self.assertTrue(root.is_absolute())
        self.assertTrue(root.exists())

    def test_path_get_core_root(self):
        """get_core_root 返回有效 core 目录"""
        core_root = ProjectContext.path.get_core_root()
        self.assertIsInstance(core_root, Path)
        self.assertTrue(core_root.is_absolute())
        self.assertEqual(core_root.name, 'core')
        self.assertTrue(core_root.exists())

    def test_path_get_userspace_root(self):
        """get_userspace_root 返回有效 userspace 目录"""
        userspace = ProjectContext.path.get_userspace_root()
        self.assertIsInstance(userspace, Path)
        self.assertTrue(userspace.is_absolute())

    def test_config_load_core_config(self):
        """load_core_config 加载并合并配置"""
        settings = ProjectContext.config.load_core_config("logging")
        self.assertIsInstance(settings, dict)

    def test_config_get_default_start_date(self):
        """get_default_start_date 返回日期字符串"""
        start_date = ProjectContext.config.get_default_start_date()
        self.assertIsInstance(start_date, str)

    def test_meta_core_version(self):
        """core_version 返回版本号或 None"""
        version = ProjectContext.meta.core_version()
        self.assertTrue(version is None or isinstance(version, str))

    def test_meta_core_info(self):
        """core_info 返回 meta 信息或 None"""
        info = ProjectContext.meta.core_info()
        self.assertTrue(info is None or isinstance(info, dict))

    def test_cache_clear_userspace_cache(self):
        """clear_userspace_cache 清理路径缓存"""
        result = ProjectContext.cache.clear_userspace_cache()
        self.assertIsNone(result)

    def test_discovery_discover_configs(self):
        """discover_configs 发现配置 ID 列表"""
        configs = ProjectContext.discovery.discover_configs()
        self.assertIsInstance(configs, list)

    def test_discovery_load_overridable_config_success(self):
        """load_overridable_config 加载并合并配置"""
        # 注意：这个测试可能会抛出异常，取决于测试环境
        try:
            config = ProjectContext.discovery.load_overridable_config("database", "common")
            self.assertIsInstance(config, dict)
        except OverridableConfigNotFoundError:
            # 测试环境没有该配置，跳过
            pass

    def test_discovery_load_overridable_config_not_found(self):
        """load_overridable_config 未找到抛出 OverridableConfigNotFoundError"""
        with self.assertRaises(OverridableConfigNotFoundError):
            ProjectContext.discovery.load_overridable_config("nonexistent_domain", "nonexistent_config")


class TestContracts(unittest.TestCase):
    """ProjectContext contracts 类型与异常"""

    def test_overridable_config_not_found_error_import(self):
        """OverridableConfigNotFoundError 可从 contracts 导入"""
        from core.infra.project_context.contracts import OverridableConfigNotFoundError
        self.assertTrue(True)  # 导入成功即测试通过

    def test_overridable_config_not_found_error_is_file_not_found_error(self):
        """OverridableConfigNotFoundError 继承 FileNotFoundError"""
        from core.infra.project_context.contracts import OverridableConfigNotFoundError
        self.assertTrue(issubclass(OverridableConfigNotFoundError, FileNotFoundError))


class TestEdgeCases(unittest.TestCase):
    """边界测试"""

    def test_empty_strategy_name(self):
        """测试空策略名称"""
        strategy_dir = ProjectContext.path.get_strategy_directory("")
        self.assertIsInstance(strategy_dir, Path)

    def test_empty_tag_name(self):
        """测试空 Tag 名称"""
        tag_dir = ProjectContext.path.get_tag_directory("")
        self.assertIsInstance(tag_dir, Path)

    def test_multiple_cache_clears(self):
        """测试多次清理缓存"""
        ProjectContext.cache.clear_userspace_cache()
        ProjectContext.cache.clear_userspace_cache()
        ProjectContext.cache.clear_userspace_cache()
        # 多次调用不应出错
        userspace = ProjectContext.path.get_userspace_root()
        self.assertIsInstance(userspace, Path)


if __name__ == "__main__":
    unittest.main()