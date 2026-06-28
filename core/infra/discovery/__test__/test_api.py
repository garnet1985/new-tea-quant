#!/usr/bin/env python3
"""
Discovery module API contract tests.

遵循 CODE_STYLE.md 规范：
- 所有测试类遵循 TestXxxApi 命名
- 所有测试方法遵循 test_xxx_api 功能命名
- 所有测试覆盖 api.yaml 中定义的稳定 API
- 分组测试、契约验证、边界测试
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Dict, Any

from core.infra.discovery import Discovery


class TestFileUtilsApi(unittest.TestCase):
    """FileUtils API 契约测试"""

    def setUp(self):
        """创建临时测试目录"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def tearDown(self):
        """清理临时测试目录"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_find_file_api_success(self):
        """测试 find_file API - 成功查找文件"""
        # 创建测试文件
        test_file = self.temp_path / "test.json"
        test_file.write_text('{"key": "value"}', encoding='utf-8')

        # 测试查找
        result = Discovery.file.find_file(self.temp_path, "test.json")
        self.assertIsNotNone(result)
        self.assertEqual(result, test_file)

    def test_find_file_api_not_found(self):
        """测试 find_file API - 未找到文件"""
        result = Discovery.file.find_file(self.temp_path, "nonexistent.json")
        self.assertIsNone(result)

    def test_find_file_api_search_parents(self):
        """测试 find_file API - 向上搜索父目录"""
        # 创建嵌套目录结构
        nested_dir = self.temp_path / "sub1" / "sub2"
        nested_dir.mkdir(parents=True)
        test_file = self.temp_path / "root.json"
        test_file.write_text('{}', encoding='utf-8')

        # 测试向上搜索
        result = Discovery.file.find_file(nested_dir, "root.json", search_parents=True)
        self.assertIsNotNone(result)
        self.assertEqual(result, test_file)

    def test_load_json_api_success(self):
        """测试 load_json API - 成功加载JSON"""
        test_file = self.temp_path / "test.json"
        test_file.write_text('{"key": "value"}', encoding='utf-8')

        result = Discovery.file.load_json(test_file)
        self.assertIsNotNone(result)
        self.assertEqual(result, {"key": "value"})

    def test_load_json_api_invalid_json(self):
        """测试 load_json API - 无效JSON格式"""
        test_file = self.temp_path / "invalid.json"
        test_file.write_text('invalid json', encoding='utf-8')

        result = Discovery.file.load_json(test_file)
        self.assertIsNone(result)

    def test_load_json_api_not_found(self):
        """测试 load_json API - 文件不存在"""
        result = Discovery.file.load_json(self.temp_path / "nonexistent.json")
        self.assertIsNone(result)

    def test_load_yaml_api_success(self):
        """测试 load_yaml API - 成功加载YAML"""
        test_file = self.temp_path / "test.yaml"
        test_file.write_text('key: value\n', encoding='utf-8')

        result = Discovery.file.load_yaml(test_file)
        self.assertIsNotNone(result)
        self.assertEqual(result, {"key": "value"})

    def test_load_yaml_api_invalid_yaml(self):
        """测试 load_yaml API - 无效YAML格式"""
        test_file = self.temp_path / "invalid.yaml"
        test_file.write_text('invalid: yaml: content:\n', encoding='utf-8')

        result = Discovery.file.load_yaml(test_file)
        self.assertIsNone(result)

    def test_load_file_content_api_json(self):
        """测试 load_file_content API - 自动识别JSON"""
        test_file = self.temp_path / "test.json"
        test_file.write_text('{"key": "value"}', encoding='utf-8')

        result = Discovery.file.load_file_content(test_file)
        self.assertIsNotNone(result)
        self.assertEqual(result, {"key": "value"})

    def test_load_file_content_api_yaml(self):
        """测试 load_file_content API - 自动识别YAML"""
        test_file = self.temp_path / "test.yaml"
        test_file.write_text('key: value\n', encoding='utf-8')

        result = Discovery.file.load_file_content(test_file)
        self.assertIsNotNone(result)
        self.assertEqual(result, {"key": "value"})

    def test_load_file_content_api_text(self):
        """测试 load_file_content API - 文本文件"""
        test_file = self.temp_path / "test.txt"
        test_file.write_text('plain text', encoding='utf-8')

        result = Discovery.file.load_file_content(test_file)
        self.assertIsNotNone(result)
        self.assertEqual(result, 'plain text')

    def test_load_python_config_api_success(self):
        """测试 load_python_config API - 成功加载Python配置"""
        test_file = self.temp_path / "settings.py"
        test_file.write_text('settings = {"key": "value"}\n', encoding='utf-8')

        result = Discovery.file.load_python_config(test_file, var_name="settings")
        self.assertIsNotNone(result)
        self.assertEqual(result, {"key": "value"})

    def test_load_python_config_api_var_not_found(self):
        """测试 load_python_config API - 变量未定义"""
        test_file = self.temp_path / "settings.py"
        test_file.write_text('other_var = {"key": "value"}\n', encoding='utf-8')

        result = Discovery.file.load_python_config(test_file, var_name="settings")
        self.assertIsNone(result)

    def test_save_file_content_api_json(self):
        """测试 save_file_content API - 保存JSON"""
        test_file = self.temp_path / "test.json"
        data = {"key": "value"}

        result = Discovery.file.save_file_content(test_file, data)
        self.assertTrue(result)

        # 验证文件内容
        loaded = Discovery.file.load_json(test_file)
        self.assertEqual(loaded, data)

    def test_save_file_content_api_yaml(self):
        """测试 save_file_content API - 保存YAML"""
        test_file = self.temp_path / "test.yaml"
        data = {"key": "value"}

        result = Discovery.file.save_file_content(test_file, data)
        self.assertTrue(result)

        # 验证文件内容
        loaded = Discovery.file.load_yaml(test_file)
        self.assertEqual(loaded, data)


class TestConvenienceFunctions(unittest.TestCase):
    """便捷函数 API 契约测试"""

    def setUp(self):
        """创建临时测试目录"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def tearDown(self):
        """清理临时测试目录"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_find_file_convenience(self):
        """测试 find_file 便捷函数"""
        test_file = self.temp_path / "test.json"
        test_file.write_text('{}', encoding='utf-8')

        result = Discovery.file.find_file(self.temp_path, "test.json")
        self.assertIsNotNone(result)

    def test_load_json_convenience(self):
        """测试 load_json 便捷函数"""
        test_file = self.temp_path / "test.json"
        test_file.write_text('{"key": "value"}', encoding='utf-8')

        result = Discovery.file.load_json(test_file)
        self.assertEqual(result, {"key": "value"})

    def test_load_python_config_convenience(self):
        """测试 load_python_config 便捷函数"""
        test_file = self.temp_path / "settings.py"
        test_file.write_text('settings = {"key": "value"}\n', encoding='utf-8')

        result = Discovery.file.load_python_config(test_file, var_name="settings")
        self.assertEqual(result, {"key": "value"})

    def test_discover_files_api(self):
        """测试 discover_files API - 批量发现文件"""
        # 创建多个JSON文件
        for i in range(3):
            test_file = self.temp_path / f"test{i}.json"
            test_file.write_text('{}', encoding='utf-8')

        result = Discovery.discover.files(self.temp_path, "*.json")
        self.assertEqual(len(result), 3)

    def test_discover_directories_api(self):
        """测试 discover_directories API - 批量发现目录"""
        # 创建多个子目录
        for i in range(3):
            sub_dir = self.temp_path / f"sub{i}"
            sub_dir.mkdir()

        result = Discovery.discover.directories(self.temp_path, "sub*")
        self.assertEqual(len(result), 3)

    def test_discover_files_by_suffix_api(self):
        """测试 discover_files_by_suffix API - 根据扩展名发现文件"""
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


class TestFileDiscoveryClass(unittest.TestCase):
    """FileDiscovery 类 API 契约测试"""

    def setUp(self):
        """创建临时测试目录"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def tearDown(self):
        """清理临时测试目录"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_file_discovery_discover_api(self):
        """测试 Discovery.discover.files API"""
        # 创建多个文件
        for i in range(3):
            test_file = self.temp_path / f"test{i}.json"
            test_file.write_text('{}', encoding='utf-8')

        # 使用 Discovery API
        result = Discovery.discover.files(self.temp_path, "*.json")
        self.assertEqual(len(result), 3)


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

    def test_permission_error(self):
        """测试权限错误（模拟）"""
        # 在实际环境中难以模拟权限错误，这里只是占位测试
        pass


class TestContractValidation(unittest.TestCase):
    """契约验证测试"""

    def test_discovery_namespace_methods(self):
        """验证 Discovery 命名空间的方法"""
        import inspect

        # 验证 file namespace 的方法
        file_methods = [
            'find_file',
            'load_file_content',
            'load_json',
            'load_yaml',
            'save_file_content',
            'load_python_config',
        ]

        for method_name in file_methods:
            method = getattr(Discovery.file, method_name)
            self.assertTrue(
                callable(method),
                f"{method_name} 应该是可调用方法"
            )

        # 验证 discover namespace 的方法
        discover_methods = [
            'files',
            'directories',
            'files_by_suffix',
        ]

        for method_name in discover_methods:
            method = getattr(Discovery.discover, method_name)
            self.assertTrue(
                callable(method),
                f"{method_name} 应该是可调用方法"
            )


if __name__ == "__main__":
    unittest.main()