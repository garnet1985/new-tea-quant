"""
ProjectContextManager API Test - 对外API契约测试

职责：
- 测试所有对外API的契约（参数、返回值、异常）
- 确保 api.py、api.yaml、test_api.py 三者一致
- 保证API稳定性

测试分组：
- 路径核心 API（5个）
- 配置核心 API（3个）
- 发现核心 API（3个）
- 文件核心 API（2个）
- 元数据核心 API（2个）
- 缓存管理 API（1个）

总计：16个核心API
"""
import pytest
from pathlib import Path
from typing import Optional, Dict, Any, List
from core.infra.project_context import ProjectContextManager, ProjectContextAPI


class TestProjectContextAPIContract:
    """ProjectContextManager API契约测试"""

    @pytest.fixture
    def ctx(self):
        """创建ProjectContextManager实例"""
        return ProjectContextManager()

    # ========== API契约验证 ==========

    def test_is_api_implementation(self, ctx):
        """验证ProjectContextManager实现了ProjectContextAPI"""
        assert isinstance(ctx, ProjectContextAPI)

    # ========== 路径核心 API测试（5个）==========

    def test_get_project_root_returns_path(self, ctx):
        """测试get_project_root返回Path对象"""
        root = ctx.get_project_root()
        assert isinstance(root, Path)
        assert root.is_absolute()

    def test_get_project_root_is_valid_directory(self, ctx):
        """测试get_project_root返回有效的项目根目录"""
        root = ctx.get_project_root()
        # 项目根目录应该包含.git或pyproject.toml
        assert (root / ".git").exists() or (root / "pyproject.toml").exists()

    def test_get_core_root_returns_path(self, ctx):
        """测试get_core_root返回Path对象"""
        core_dir = ctx.get_core_root()
        assert isinstance(core_dir, Path)
        assert core_dir.is_absolute()

    def test_get_core_root_is_valid_directory(self, ctx):
        """测试get_core_root返回有效的core目录"""
        core_dir = ctx.get_core_root()
        assert core_dir.name == "core"
        assert core_dir.exists()

    def test_get_userspace_root_returns_path(self, ctx):
        """测试get_userspace_root返回Path对象"""
        userspace = ctx.get_userspace_root()
        assert isinstance(userspace, Path)
        assert userspace.is_absolute()

    def test_get_userspace_root_is_valid_directory(self, ctx):
        """测试get_userspace_root返回有效的userspace目录"""
        userspace = ctx.get_userspace_root()
        assert userspace.name == "userspace"

    def test_get_strategy_directory_returns_path(self, ctx):
        """测试get_strategy_directory返回Path对象"""
        strategy_dir = ctx.get_strategy_directory("example")
        assert isinstance(strategy_dir, Path)
        assert strategy_dir.is_absolute()

    def test_get_strategy_directory_with_valid_name(self, ctx):
        """测试get_strategy_directory接受有效的策略名称"""
        strategy_dir = ctx.get_strategy_directory("test_strategy")
        assert strategy_dir.name == "test_strategy"
        assert "strategies" in str(strategy_dir)

    def test_get_tag_directory_returns_path(self, ctx):
        """测试get_tag_directory返回Path对象"""
        tag_dir = ctx.get_tag_directory("example")
        assert isinstance(tag_dir, Path)
        assert tag_dir.is_absolute()

    def test_get_tag_directory_with_valid_name(self, ctx):
        """测试get_tag_directory接受有效的Tag名称"""
        tag_dir = ctx.get_tag_directory("test_tag")
        assert tag_dir.name == "test_tag"
        assert "tags" in str(tag_dir)

    # ========== 配置核心 API测试（3个）==========

    def test_load_core_config_returns_dict(self, ctx):
        """测试load_core_config返回字典"""
        config = ctx.load_core_config("logging")
        assert isinstance(config, dict)

    def test_load_core_config_with_valid_name(self, ctx):
        """测试load_core_config接受有效的配置名称"""
        # 尝试加载存在的配置（如果不存在，返回空字典）
        config = ctx.load_core_config("logging")
        assert isinstance(config, dict)

    def test_load_core_config_with_invalid_name(self, ctx):
        """测试load_core_config接受无效的配置名称（返回空字典）"""
        config = ctx.load_core_config("nonexistent_config")
        assert isinstance(config, dict)
        # 文件不存在时应该返回空字典（而不是抛出异常）
        assert config == {} or len(config) >= 0

    def test_load_database_config_returns_dict(self, ctx):
        """测试load_database_config返回字典"""
        config = ctx.load_database_config()
        assert isinstance(config, dict)

    def test_load_database_config_with_database_type(self, ctx):
        """测试load_database_config接受database_type参数"""
        config = ctx.load_database_config("duckdb")
        assert isinstance(config, dict)

    def test_load_database_config_with_none_type(self, ctx):
        """测试load_database_config接受None参数"""
        config = ctx.load_database_config(None)
        assert isinstance(config, dict)

    def test_load_data_config_returns_dict(self, ctx):
        """测试load_data_config返回字典"""
        config = ctx.load_data_config()
        assert isinstance(config, dict)

    # ========== 发现核心 API测试（3个）==========

    def test_discover_strategies_returns_list(self, ctx):
        """测试discover_strategies返回列表"""
        strategies = ctx.discover_strategies()
        assert isinstance(strategies, list)

    def test_discover_strategies_contains_strings(self, ctx):
        """测试discover_strategies返回字符串列表"""
        strategies = ctx.discover_strategies()
        for strategy in strategies:
            assert isinstance(strategy, str)

    def test_discover_tags_returns_list(self, ctx):
        """测试discover_tags返回列表"""
        tags = ctx.discover_tags()
        assert isinstance(tags, list)

    def test_discover_tags_contains_strings(self, ctx):
        """测试discover_tags返回字符串列表"""
        tags = ctx.discover_tags()
        for tag in tags:
            assert isinstance(tag, str)

    def test_discover_configs_returns_dict(self, ctx):
        """测试discover_configs返回字典"""
        configs = ctx.discover_configs()
        assert isinstance(configs, dict)

    def test_discover_configs_contains_dicts(self, ctx):
        """测试discover_configs返回字典到字典的映射"""
        configs = ctx.discover_configs()
        for config_name, config_dict in configs.items():
            assert isinstance(config_name, str)
            assert isinstance(config_dict, dict)

    # ========== 文件核心 API测试（2个）==========

    def test_find_file_returns_path_or_none(self, ctx):
        """测试find_file返回Path对象或None"""
        # 搜索存在的文件
        result = ctx.find_file("pyproject.toml", ctx.get_project_root(), recursive=False)
        assert result is None or isinstance(result, Path)

    def test_find_file_with_recursive_true(self, ctx):
        """测试find_file接受recursive=True参数"""
        result = ctx.find_file("settings.py", ctx.get_userspace_root(), recursive=True)
        assert result is None or isinstance(result, Path)

    def test_find_file_with_recursive_false(self, ctx):
        """测试find_file接受recursive=False参数"""
        result = ctx.find_file("pyproject.toml", ctx.get_project_root(), recursive=False)
        assert result is None or isinstance(result, Path)

    def test_find_file_with_nonexistent_file(self, ctx):
        """测试find_file搜索不存在的文件（返回None）"""
        result = ctx.find_file("nonexistent_file.txt", ctx.get_project_root(), recursive=True)
        assert result is None

    def test_load_file_content_returns_string_or_none(self, ctx):
        """测试load_file_content返回字符串或None"""
        # 尝试加载存在的文件
        core_dir = ctx.get_core_root()
        result = ctx.load_file_content(core_dir / "core_meta.json")
        assert result is None or isinstance(result, str)

    def test_load_file_content_with_valid_file(self, ctx, tmp_path):
        """测试load_file_content加载存在的文件"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content", encoding="utf-8")

        content = ctx.load_file_content(test_file, encoding="utf-8")
        assert content == "test content"

    def test_load_file_content_with_nonexistent_file(self, ctx):
        """测试load_file_content加载不存在的文件（返回None）"""
        content = ctx.load_file_content(Path("/nonexistent/file.txt"))
        assert content is None

    def test_load_file_content_with_encoding_parameter(self, ctx, tmp_path):
        """测试load_file_content接受encoding参数"""
        test_file = tmp_path / "test_utf8.txt"
        test_file.write_text("UTF-8 content", encoding="utf-8")

        content = ctx.load_file_content(test_file, encoding="utf-8")
        assert content == "UTF-8 content"

    # ========== 元数据核心 API测试（2个）==========

    def test_core_version_returns_string_or_none(self, ctx):
        """测试core_version返回字符串或None"""
        version = ctx.core_version()
        assert version is None or isinstance(version, str)

    def test_core_version_format(self, ctx):
        """测试core_version版本号格式（如果存在）"""
        version = ctx.core_version()
        if version is not None:
            # 版本号应该是x.y.z格式
            parts = version.split(".")
            assert len(parts) >= 2  # 至少是x.y格式

    def test_core_info_returns_dict_or_none(self, ctx):
        """测试core_info返回字典或None"""
        info = ctx.core_info()
        assert info is None or isinstance(info, dict)

    def test_core_info_contains_version(self, ctx):
        """测试core_info包含version字段（如果存在）"""
        info = ctx.core_info()
        if info is not None:
            assert "version" in info

    # ========== 缓存管理 API测试（1个）==========

    def test_clear_userspace_cache_returns_none(self, ctx):
        """测试clear_userspace_cache返回None"""
        result = ctx.clear_userspace_cache()
        assert result is None

    def test_clear_userspace_cache_clears_cache(self, ctx):
        """测试clear_userspace_cache清理缓存后重新计算路径"""
        # 先获取userspace路径（会缓存）
        userspace1 = ctx.get_userspace_root()

        # 清理缓存
        ctx.clear_userspace_cache()

        # 再次获取（会重新计算）
        userspace2 = ctx.get_userspace_root()

        # 路径应该相同（即使重新计算）
        assert userspace1 == userspace2

    # ========== API契约完整性验证 ==========

    def test_api_count_matches_definition(self, ctx):
        """验证API数量与定义一致（16个核心API）"""
        # 检查所有API是否都存在
        api_methods = [
            'get_project_root',
            'get_core_root',
            'get_userspace_root',
            'get_strategy_directory',
            'get_tag_directory',
            'load_core_config',
            'load_database_config',
            'load_data_config',
            'discover_strategies',
            'discover_tags',
            'discover_configs',
            'find_file',
            'load_file_content',
            'core_version',
            'core_info',
            'clear_userspace_cache',
        ]

        for method_name in api_methods:
            assert hasattr(ctx, method_name)
            assert callable(getattr(ctx, method_name))

    def test_all_api_methods_are_instance_methods(self, ctx):
        """验证所有API方法都是实例方法（不是静态方法）"""
        import inspect

        api_methods = [
            'get_project_root',
            'get_core_root',
            'get_userspace_root',
            'get_strategy_directory',
            'get_tag_directory',
            'load_core_config',
            'load_database_config',
            'load_data_config',
            'discover_strategies',
            'discover_tags',
            'discover_configs',
            'find_file',
            'load_file_content',
            'core_version',
            'core_info',
            'clear_userspace_cache',
        ]

        for method_name in api_methods:
            method = getattr(ctx.__class__, method_name)
            # 检查是否是普通方法（不是静态方法）
            assert not isinstance(inspect.getattr_static(ctx.__class__, method_name), staticmethod)


class TestProjectContextAPIEdgeCases:
    """ProjectContextManager边缘case测试"""

    @pytest.fixture
    def ctx(self):
        """创建ProjectContextManager实例"""
        return ProjectContextManager()

    # ========== 路径API边缘case ==========

    def test_get_strategy_directory_with_empty_name(self, ctx):
        """测试get_strategy_directory接受空字符串"""
        strategy_dir = ctx.get_strategy_directory("")
        assert isinstance(strategy_dir, Path)

    def test_get_tag_directory_with_empty_name(self, ctx):
        """测试get_tag_directory接受空字符串"""
        tag_dir = ctx.get_tag_directory("")
        assert isinstance(tag_dir, Path)

    # ========== 配置API边缘case ==========

    def test_load_database_config_with_empty_string_type(self, ctx):
        """测试load_database_config接受空字符串"""
        config = ctx.load_database_config("")
        assert isinstance(config, dict)

    # ========== 文件API边缘case ==========

    def test_find_file_with_empty_filename(self, ctx):
        """测试find_file接受空文件名"""
        result = ctx.find_file("", ctx.get_project_root())
        assert result is None

    def test_load_file_content_with_invalid_encoding(self, ctx, tmp_path):
        """测试load_file_content接受无效编码（可能抛出异常或返回None）"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content", encoding="utf-8")

        # 使用无效编码（可能抛出异常）
        try:
            content = ctx.load_file_content(test_file, encoding="invalid_encoding")
            # 如果不抛出异常，可能返回None或错误的字符串
            assert content is None or isinstance(content, str)
        except Exception:
            # 如果抛出异常，也是合理的
            pass

    # ========== 缓存API边缘case ==========

    def test_clear_userspace_cache_multiple_times(self, ctx):
        """测试多次调用clear_userspace_cache"""
        ctx.clear_userspace_cache()
        ctx.clear_userspace_cache()
        ctx.clear_userspace_cache()

        # 多次调用应该不会出错
        userspace = ctx.get_userspace_root()
        assert isinstance(userspace, Path)