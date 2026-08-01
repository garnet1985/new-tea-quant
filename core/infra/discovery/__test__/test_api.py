#!/usr/bin/env python3
"""对齐根目录 API.md 的契约测试。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pytest

from core.infra.discovery import Discovery

pytestmark = pytest.mark.force_run


class TestApi(unittest.TestCase):
    """Discovery API 契约测试"""

    def setUp(self):
        """创建临时测试目录"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def tearDown(self):
        """清理临时测试目录"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_facade_export(self):
        """facade 导出 file / discover / class_discovery namespace"""
        import core.infra.discovery as pkg

        self.assertEqual(pkg.__all__, ["Discovery"])
        self.assertTrue(hasattr(Discovery, "file"))
        self.assertTrue(hasattr(Discovery, "discover"))
        self.assertTrue(hasattr(Discovery, "class_discovery"))

    def test_contracts_symbols(self):
        from core.infra.discovery import contracts

        for name in (
            "DiscoveryConfig",
            "DiscoveryResult",
            "ClassDiscovery",
            "FileDiscoveryConfig",
        ):
            self.assertTrue(hasattr(contracts, name), name)

    def test_file_namespace_methods(self):
        """file namespace 包含所有文件操作 API"""
        methods = [
            'find_file',
            'load_file_content',
            'load_json',
            'load_yaml',
            'load_text',
            'load_python_config',
            'save_file_content',
            'save_json',
            'save_yaml',
        ]
        for method_name in methods:
            method = getattr(Discovery.file, method_name)
            self.assertTrue(callable(method), f"{method_name} should be callable")

    def test_discover_namespace_methods(self):
        """discover namespace 包含批量发现 API"""
        methods = [
            'files',
            'directories',
            'files_by_suffix',
            'subclasses',
            'objects',
        ]
        for method_name in methods:
            method = getattr(Discovery.discover, method_name)
            self.assertTrue(callable(method), f"{method_name} should be callable")

    def test_class_discovery_namespace_methods(self):
        """class_discovery namespace 包含类发现 API"""
        methods = [
            'create_config',
            'create',
            'discover_class_by_path',
        ]
        for method_name in methods:
            method = getattr(Discovery.class_discovery, method_name)
            self.assertTrue(callable(method), f"{method_name} should be callable")

    def test_file_find_file_success(self):
        """find_file 成功查找文件"""
        # 创建测试文件
        test_file = self.temp_path / "test.json"
        test_file.write_text('{"key": "value"}', encoding='utf-8')

        # 测试查找
        result = Discovery.file.find_file(self.temp_path, "test.json")
        self.assertIsNotNone(result)
        self.assertEqual(result, test_file)

    def test_file_find_file_not_found(self):
        """find_file 未找到返回 None"""
        result = Discovery.file.find_file(self.temp_path, "nonexistent.json")
        self.assertIsNone(result)

    def test_file_find_file_search_parents(self):
        """find_file 向上搜索父目录"""
        # 创建嵌套目录结构
        nested_dir = self.temp_path / "sub1" / "sub2"
        nested_dir.mkdir(parents=True)
        test_file = self.temp_path / "root.json"
        test_file.write_text('{}', encoding='utf-8')

        # 测试向上搜索
        result = Discovery.file.find_file(nested_dir, "root.json", search_parents=True)
        self.assertIsNotNone(result)
        self.assertEqual(result, test_file)

    def test_file_load_json_success(self):
        """load_json 成功加载 JSON"""
        test_file = self.temp_path / "test.json"
        test_file.write_text('{"key": "value"}', encoding='utf-8')

        result = Discovery.file.load_json(test_file)
        self.assertIsNotNone(result)
        self.assertEqual(result, {"key": "value"})

    def test_file_load_json_invalid(self):
        """load_json 无效 JSON 返回 None"""
        test_file = self.temp_path / "invalid.json"
        test_file.write_text('invalid json', encoding='utf-8')

        result = Discovery.file.load_json(test_file)
        self.assertIsNone(result)

    def test_file_load_yaml_success(self):
        """load_yaml 成功加载 YAML"""
        test_file = self.temp_path / "test.yaml"
        test_file.write_text('key: value\n', encoding='utf-8')

        result = Discovery.file.load_yaml(test_file)
        self.assertIsNotNone(result)
        self.assertEqual(result, {"key": "value"})

    def test_file_load_file_content_json(self):
        """load_file_content 自动识别 JSON"""
        test_file = self.temp_path / "test.json"
        test_file.write_text('{"key": "value"}', encoding='utf-8')

        result = Discovery.file.load_file_content(test_file)
        self.assertIsNotNone(result)
        self.assertEqual(result, {"key": "value"})

    def test_file_load_file_content_yaml(self):
        """load_file_content 自动识别 YAML"""
        test_file = self.temp_path / "test.yaml"
        test_file.write_text('key: value\n', encoding='utf-8')

        result = Discovery.file.load_file_content(test_file)
        self.assertIsNotNone(result)
        self.assertEqual(result, {"key": "value"})

    def test_file_load_file_content_text(self):
        """load_file_content 加载文本文件"""
        test_file = self.temp_path / "test.txt"
        test_file.write_text('plain text', encoding='utf-8')

        result = Discovery.file.load_file_content(test_file)
        self.assertIsNotNone(result)
        self.assertEqual(result, 'plain text')

    def test_file_load_python_config_success(self):
        """load_python_config 成功加载 Python 配置"""
        test_file = self.temp_path / "settings.py"
        test_file.write_text('settings = {"key": "value"}\n', encoding='utf-8')

        result = Discovery.file.load_python_config(test_file, var_name="settings")
        self.assertIsNotNone(result)
        self.assertEqual(result, {"key": "value"})

    def test_file_save_file_content_json(self):
        """save_file_content 保存 JSON"""
        test_file = self.temp_path / "test.json"
        data = {"key": "value"}

        result = Discovery.file.save_file_content(test_file, data)
        self.assertTrue(result)

        # 验证文件内容
        loaded = Discovery.file.load_json(test_file)
        self.assertEqual(loaded, data)

    def test_file_save_file_content_yaml(self):
        """save_file_content 保存 YAML"""
        test_file = self.temp_path / "test.yaml"
        data = {"key": "value"}

        result = Discovery.file.save_file_content(test_file, data)
        self.assertTrue(result)

        # 验证文件内容
        loaded = Discovery.file.load_yaml(test_file)
        self.assertEqual(loaded, data)

    def test_discover_files(self):
        """discover.files 批量发现文件"""
        # 创建多个JSON文件
        for i in range(3):
            test_file = self.temp_path / f"test{i}.json"
            test_file.write_text('{}', encoding='utf-8')

        result = Discovery.discover.files(self.temp_path, "*.json")
        self.assertEqual(len(result), 3)

    def test_discover_directories(self):
        """discover.directories 批量发现目录"""
        # 创建多个子目录
        for i in range(3):
            sub_dir = self.temp_path / f"sub{i}"
            sub_dir.mkdir()

        result = Discovery.discover.directories(self.temp_path, "sub*")
        self.assertEqual(len(result), 3)

    def test_discover_files_by_suffix(self):
        """discover.files_by_suffix 根据扩展名发现文件"""
        # 创建多个JSON文件
        for i in range(3):
            test_file = self.temp_path / f"test{i}.json"
            test_file.write_text('{}', encoding='utf-8')

        # 创建其他类型的文件
        txt_file = self.temp_path / "test.txt"
        txt_file.write_text('text', encoding='utf-8')

        result = Discovery.discover.files_by_suffix(self.temp_path, ".json")
        self.assertEqual(len(result), 3)
        # 确保不包含txt文件
        for path in result:
            self.assertTrue(path.suffix == ".json")

    def test_discover_subclasses(self):
        """discover.subclasses 发现子类"""
        # 注意：这个测试需要在真实环境中运行
        # 这里只是测试方法可调用性
        self.assertTrue(callable(Discovery.discover.subclasses))

    def test_discover_objects(self):
        """discover.objects 发现模块对象"""
        # 注意：这个测试需要在真实环境中运行
        # 这里只是测试方法可调用性
        self.assertTrue(callable(Discovery.discover.objects))

    def test_class_discovery_create_config(self):
        """class_discovery.create_config 创建配置"""
        # 注意：这个测试需要在真实环境中运行
        # 这里只是测试方法可调用性
        self.assertTrue(callable(Discovery.class_discovery.create_config))

    def test_class_discovery_discover_class_by_path(self):
        """class_discovery.discover_class_by_path 发现类"""
        # 注意：这个测试需要在真实环境中运行
        # 这里只是测试方法可调用性
        self.assertTrue(callable(Discovery.class_discovery.discover_class_by_path))


class TestEdgeCases(unittest.TestCase):
    """边界测试"""

    def setUp(self):
        """创建临时测试目录"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def tearDown(self):
        """清理临时测试目录"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_empty_directory(self):
        """测试空目录"""
        result = Discovery.discover.files(self.temp_path, "*.json")
        self.assertEqual(len(result), 0)

    def test_nested_directory(self):
        """测试嵌套目录"""
        # 创建嵌套文件
        nested_dir = self.temp_path / "sub1" / "sub2"
        nested_dir.mkdir(parents=True)
        test_file = nested_dir / "test.json"
        test_file.write_text('{}', encoding='utf-8')

        # 测试递归发现
        result = Discovery.discover.files(self.temp_path, "**/*.json")
        self.assertEqual(len(result), 1)

    def test_max_depth_limit(self):
        """测试最大深度限制"""
        # 创建深层嵌套文件
        deep_dir = self.temp_path / "l1" / "l2" / "l3" / "l4" / "l5"
        deep_dir.mkdir(parents=True)
        test_file = deep_dir / "test.json"
        test_file.write_text('{}', encoding='utf-8')

        # 测试深度限制
        result = Discovery.discover.files(self.temp_path, "**/*.json", max_depth=3)
        self.assertEqual(len(result), 0)  # 超过深度限制


if __name__ == "__main__":
    unittest.main()