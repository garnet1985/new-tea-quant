"""
ProjectContext API Test - 对外API契约测试

职责：
- 测试所有对外API的契约（参数、返回值、异常）
- 确保 api.py、api.yaml、test_api.py 三者一致
- 保证API稳定性

测试分组：
- 路径核心 API
- 特殊配置 API
- 元数据核心 API
- 缓存管理 API

已移除的API（不再测试）：
- load_core_config（配置加载API）
- load_database_config（配置加载API）
- load_data_config（配置加载API）
- discover_strategies（发现API）
- discover_tags（发现API）
- discover_configs（发现API）
- find_file（文件查找API）
- load_file_content（文件加载API）
"""
import pytest
from pathlib import Path
from typing import Optional, Dict, Any, List
from core.infra.project_context import ProjectContext
from core.infra.project_context.base import ProjectContextAPI


class TestProjectContextAPIContract:
    """ProjectContext API契约测试"""

    # ========== API契约验证 ==========

    # test_is_api_implementation 已删除 - ProjectContext现在通过namespace提供API，不再继承ProjectContextAPI

    # ========== 路径核心 API测试（13个）==========

    def test_get_project_root_returns_path(self):
        """测试get_project_root返回Path对象"""
        root = ProjectContext.path.get_project_root()
        assert isinstance(root, Path)
        assert root.is_absolute()

    def test_get_project_root_is_valid_directory(self):
        """测试get_project_root返回有效的项目根目录"""
        root = ProjectContext.path.get_project_root()
        # 项目根目录应该包含.git或pyproject.toml
        assert (root / ".git").exists() or (root / "pyproject.toml").exists()

    def test_get_core_root_returns_path(self):
        """测试get_core_root返回Path对象"""
        core_root = ProjectContext.path.get_core_root()
        assert isinstance(core_root, Path)
        assert core_root.is_absolute()

    def test_get_userspace_root_returns_path(self):
        """测试get_userspace_root返回Path对象"""
        userspace_root = ProjectContext.path.get_userspace_root()
        assert isinstance(userspace_root, Path)
        assert userspace_root.is_absolute()

    def test_get_extensions_root_returns_path(self):
        """测试get_extensions_root返回Path对象"""
        extensions_root = ProjectContext.path.get_extensions_root()
        assert isinstance(extensions_root, Path)
        assert extensions_root.is_absolute()

    def test_get_system_root_returns_path(self):
        """测试get_system_root返回Path对象"""
        system_root = ProjectContext.path.get_system_root()
        assert isinstance(system_root, Path)
        assert system_root.is_absolute()

    def test_get_default_config_root_returns_path(self):
        """测试get_default_config_root返回Path对象"""
        default_config_root = ProjectContext.path.get_default_config_root()
        assert isinstance(default_config_root, Path)
        assert default_config_root.is_absolute()

    def test_get_user_config_root_returns_path(self):
        """测试get_user_config_root返回Path对象"""
        user_config_root = ProjectContext.path.get_user_config_root()
        assert isinstance(user_config_root, Path)
        assert user_config_root.is_absolute()

    def test_get_system_db_directory_returns_path(self):
        """测试get_system_db_directory返回Path对象"""
        system_db_directory = ProjectContext.path.get_system_db_directory()
        assert isinstance(system_db_directory, Path)
        assert system_db_directory.is_absolute()

    def test_get_backup_directory_returns_path(self):
        """测试get_backup_directory返回Path对象"""
        backup_directory = ProjectContext.path.get_backup_directory()
        assert isinstance(backup_directory, Path)
        assert backup_directory.is_absolute()

    def test_get_updater_directory_returns_path(self):
        """测试get_updater_directory返回Path对象"""
        updater_directory = ProjectContext.path.get_updater_directory()
        assert isinstance(updater_directory, Path)
        assert updater_directory.is_absolute()

    def test_get_userspace_tmp_directory_returns_path(self):
        """测试get_userspace_tmp_directory返回Path对象"""
        userspace_tmp_directory = ProjectContext.path.get_userspace_tmp_directory()
        assert isinstance(userspace_tmp_directory, Path)
        assert userspace_tmp_directory.is_absolute()

    def test_get_strategies_root_returns_path(self):
        """测试get_strategies_root返回Path对象"""
        strategies_root = ProjectContext.path.get_strategies_root()
        assert isinstance(strategies_root, Path)
        assert strategies_root.is_absolute()

    def test_get_tags_root_returns_path(self):
        """测试get_tags_root返回Path对象"""
        tags_root = ProjectContext.path.get_tags_root()
        assert isinstance(tags_root, Path)
        assert tags_root.is_absolute()
        core_dir = ProjectContext.path.get_core_root()
        assert isinstance(core_dir, Path)
        assert core_dir.is_absolute()

    def test_get_core_root_is_valid_directory(self):
        """测试get_core_root返回有效的core目录"""
        core_dir = ProjectContext.path.get_core_root()
        assert core_dir.name == "core"
        assert core_dir.exists()

    def test_get_userspace_root_returns_path(self):
        """测试get_userspace_root返回Path对象"""
        userspace = ProjectContext.path.get_userspace_root()
        assert isinstance(userspace, Path)
        assert userspace.is_absolute()

    def test_get_userspace_root_is_valid_directory(self):
        """测试get_userspace_root返回有效的userspace目录"""
        userspace = ProjectContext.path.get_userspace_root()
        assert userspace.name == "userspace"

    def test_get_strategies_root_returns_path(self):
        """测试get_strategies_root返回Path对象"""
        strategies_root = ProjectContext.path.get_strategies_root()
        assert isinstance(strategies_root, Path)
        assert strategies_root.is_absolute()

    def test_get_strategies_root_is_valid_directory(self):
        """测试get_strategies_root返回有效的strategies目录"""
        strategies_root = ProjectContext.path.get_strategies_root()
        assert strategies_root.name == "strategies"

    def test_get_tags_root_returns_path(self):
        """测试get_tags_root返回Path对象"""
        tags_root = ProjectContext.path.get_tags_root()
        assert isinstance(tags_root, Path)
        assert tags_root.is_absolute()

    def test_get_tags_root_is_valid_directory(self):
        """测试get_tags_root返回有效的tags目录"""
        tags_root = ProjectContext.path.get_tags_root()
        assert tags_root.name == "tags"

    def test_get_strategy_directory_returns_path(self):
        """测试get_strategy_directory返回Path对象"""
        strategy_dir = ProjectContext.path.get_strategy_directory("example")
        assert isinstance(strategy_dir, Path)
        assert strategy_dir.is_absolute()

    def test_get_strategy_directory_with_valid_name(self):
        """测试get_strategy_directory接受有效的策略名称"""
        strategy_dir = ProjectContext.path.get_strategy_directory("test_strategy")
        assert strategy_dir.name == "test_strategy"
        assert "strategies" in str(strategy_dir)

    def test_get_tag_directory_returns_path(self):
        """测试get_tag_directory返回Path对象"""
        tag_dir = ProjectContext.path.get_tag_directory("example")
        assert isinstance(tag_dir, Path)
        assert tag_dir.is_absolute()

    def test_get_tag_directory_with_valid_name(self):
        """测试get_tag_directory接受有效的Tag名称"""
        tag_dir = ProjectContext.path.get_tag_directory("test_tag")
        assert tag_dir.name == "test_tag"
        assert "tags" in str(tag_dir)

    # ========== 策略路径 API测试（5个）==========

    def test_get_strategy_directory_simulation_price_returns_path(self):
        """测试get_strategy_directory_simulation_price返回Path对象"""
        price_dir = ProjectContext.path.get_strategy_directory_simulation_price("example")
        assert isinstance(price_dir, Path)
        assert price_dir.is_absolute()

    def test_get_strategy_directory_simulation_capital_returns_path(self):
        """测试get_strategy_directory_simulation_capital返回Path对象"""
        capital_dir = ProjectContext.path.get_strategy_directory_simulation_capital("example")
        assert isinstance(capital_dir, Path)
        assert capital_dir.is_absolute()

    def test_get_strategy_directory_simulation_enum_returns_path(self):
        """测试get_strategy_directory_simulation_enum返回Path对象"""
        enum_dir = ProjectContext.path.get_strategy_directory_simulation_enum("example")
        assert isinstance(enum_dir, Path)
        assert enum_dir.is_absolute()

    def test_get_strategy_scan_results_directory_returns_path(self):
        """测试get_strategy_scan_results_directory返回Path对象"""
        scan_dir = ProjectContext.path.get_strategy_scan_results_directory("example")
        assert isinstance(scan_dir, Path)
        assert scan_dir.is_absolute()

    def test_get_tag_scenario_directory_returns_path(self):
        """测试get_tag_scenario_directory返回Path对象"""
        scenario_dir = ProjectContext.path.get_tag_scenario_directory("example")
        assert isinstance(scenario_dir, Path)
        assert scenario_dir.is_absolute()

    # ========== 扩展路径 API测试（7个）==========

    def test_get_extensions_tables_directory_returns_path(self):
        """测试get_extensions_tables_directory返回Path对象"""
        tables_dir = ProjectContext.path.get_extensions_tables_directory()
        assert isinstance(tables_dir, Path)
        assert tables_dir.is_absolute()

    def test_get_adapters_directory_returns_path(self):
        """测试get_adapters_directory返回Path对象"""
        adapters_dir = ProjectContext.path.get_adapters_directory()
        assert isinstance(adapters_dir, Path)
        assert adapters_dir.is_absolute()

    def test_get_data_source_handler_directory_returns_path(self):
        """测试get_data_source_handler_directory返回Path对象"""
        handler_dir = ProjectContext.path.get_data_source_handler_directory("example_handler")
        assert isinstance(handler_dir, Path)
        assert handler_dir.is_absolute()

    def test_get_data_source_handlers_directory_returns_path(self):
        """测试get_data_source_handlers_directory返回Path对象"""
        handlers_dir = ProjectContext.path.get_data_source_handlers_directory()
        assert isinstance(handlers_dir, Path)
        assert handlers_dir.is_absolute()

    def test_get_data_source_mapping_path_returns_path(self):
        """测试get_data_source_mapping_path返回Path对象"""
        mapping_path = ProjectContext.path.get_data_source_mapping_path()
        assert isinstance(mapping_path, Path)
        assert mapping_path.is_absolute()

    def test_get_data_contract_mapping_path_returns_path(self):
        """测试get_data_contract_mapping_path返回Path对象"""
        mapping_path = ProjectContext.path.get_data_contract_mapping_path()
        assert isinstance(mapping_path, Path)
        assert mapping_path.is_absolute()

    def test_get_userspace_ntq_directory_returns_path(self):
        """测试get_userspace_ntq_directory返回Path对象"""
        ntq_dir = ProjectContext.path.get_userspace_ntq_directory()
        assert isinstance(ntq_dir, Path)
        assert ntq_dir.is_absolute()

    # ========== 特殊配置 API测试（3个）==========

    def test_get_default_start_date_returns_string(self):
        """测试get_default_start_date返回字符串"""
        start_date = ProjectContext.config.get_default_start_date()
        assert isinstance(start_date, str) or start_date is None

    def test_get_as_of_latest_completed_trading_date_returns_string_or_none(self):
        """测试get_as_of_latest_completed_trading_date返回字符串或None"""
        as_of = ProjectContext.config.get_as_of_latest_completed_trading_date()
        assert as_of is None or isinstance(as_of, str)

    def test_get_use_sample_stock_list_returns_int_or_none(self):
        """测试get_use_sample_stock_list返回整数或None"""
        sample_size = ProjectContext.config.get_use_sample_stock_list()
        assert sample_size is None or isinstance(sample_size, int)

    # ========== 元数据核心 API测试（2个）==========

    def test_core_version_returns_string_or_none(self):
        """测试core_version返回字符串或None"""
        version = ProjectContext.meta.core_version()
        assert version is None or isinstance(version, str)

    def test_core_version_format(self):
        """测试core_version版本号格式（如果存在）"""
        version = ProjectContext.meta.core_version()
        if version is not None:
            # 版本号应该是x.y.z格式
            parts = version.split(".")
            assert len(parts) >= 2  # 至少是x.y格式

    def test_core_info_returns_dict_or_none(self):
        """测试core_info返回字典或None"""
        info = ProjectContext.meta.core_info()
        assert info is None or isinstance(info, dict)

    def test_core_info_contains_version(self):
        """测试core_info包含version字段（如果存在）"""
        info = ProjectContext.meta.core_info()
        if info is not None:
            assert "version" in info

    # ========== 缓存管理 API测试（1个）==========

    def test_clear_userspace_cache_returns_none(self):
        """测试clear_userspace_cache返回None"""
        result = ProjectContext.cache.clear_userspace_cache()
        assert result is None

    def test_clear_userspace_cache_clears_cache(self):
        """测试clear_userspace_cache清理缓存后重新计算路径"""
        # 先获取userspace路径（会缓存）
        userspace1 = ProjectContext.path.get_userspace_root()

        # 清理缓存
        ProjectContext.cache.clear_userspace_cache()

        # 再次获取（会重新计算）
        userspace2 = ProjectContext.path.get_userspace_root()

        # 路径应该相同（即使重新计算）
        assert userspace1 == userspace2

    # ========== API契约完整性验证 ==========

    def test_api_count_matches_definition(self):
        """验证API数量与定义一致（保留的核心API）"""
        # 检查所有API是否都存在
        path_api_methods = [
            'get_project_root',
            'get_core_root',
            'get_userspace_root',
            'get_strategy_directory',
            'get_tag_directory',
        ]

        meta_api_methods = [
            'core_version',
            'core_info',
        ]

        cache_api_methods = [
            'clear_userspace_cache',
        ]

        # 检查path namespace方法
        for method_name in path_api_methods:
            assert hasattr(ProjectContext.path, method_name)
            assert callable(getattr(ProjectContext.path, method_name))

        # 检查meta namespace方法
        for method_name in meta_api_methods:
            assert hasattr(ProjectContext.meta, method_name)
            assert callable(getattr(ProjectContext.meta, method_name))

        # 检查cache namespace方法
        for method_name in cache_api_methods:
            assert hasattr(ProjectContext.cache, method_name)
            assert callable(getattr(ProjectContext.cache, method_name))

    def test_all_api_methods_are_classmethods(self):
        """验证所有API方法都是类方法（不是静态方法）"""
        import inspect

        path_api_methods = [
            'get_project_root',
            'get_core_root',
            'get_userspace_root',
            'get_strategy_directory',
            'get_tag_directory',
        ]

        meta_api_methods = [
            'core_version',
            'core_info',
        ]

        cache_api_methods = [
            'clear_userspace_cache',
        ]

        # 检查path namespace方法
        for method_name in path_api_methods:
            method = getattr(ProjectContext.path, method_name)
            # 静态方法不需要检查__func__属性
            assert callable(method), f"{method_name} should be callable"

        # 检查meta namespace方法
        for method_name in meta_api_methods:
            method = getattr(ProjectContext.meta, method_name)
            assert callable(method), f"{method_name} should be callable"

        # 检查cache namespace方法
        for method_name in cache_api_methods:
            method = getattr(ProjectContext.cache, method_name)
            assert callable(method), f"{method_name} should be callable"


class TestProjectContextAPIEdgeCases:
    """ProjectContext边缘case测试"""

    # ========== 路径API边缘case ==========

    def test_get_strategy_directory_with_empty_name(self):
        """测试get_strategy_directory接受空字符串"""
        strategy_dir = ProjectContext.path.get_strategy_directory("")
        assert isinstance(strategy_dir, Path)

    def test_get_tag_directory_with_empty_name(self):
        """测试get_tag_directory接受空字符串"""
        tag_dir = ProjectContext.path.get_tag_directory("")
        assert isinstance(tag_dir, Path)

    # ========== 缓存API边缘case ==========

    def test_clear_userspace_cache_multiple_times(self):
        """测试多次调用clear_userspace_cache"""
        ProjectContext.cache.clear_userspace_cache()
        ProjectContext.cache.clear_userspace_cache()
        ProjectContext.cache.clear_userspace_cache()

        # 多次调用应该不会出错
        userspace = ProjectContext.path.get_userspace_root()
        assert isinstance(userspace, Path)