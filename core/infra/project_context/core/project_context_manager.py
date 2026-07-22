"""Project Context Manager - 项目上下文管理器"""
import json
from pathlib import Path
from typing import Optional, Dict, Any

from ..base import ProjectContextAPI
from .path_manager import PathManager
from .namespaces import PathNamespace, MetaNamespace, CacheNamespace


class ProjectContext(ProjectContextAPI):
    """Project Context Manager - 对外唯一入口（路径快捷入口）"""

    # ========== Namespace API（推荐使用）==========

    # 路径命名空间
    path = PathNamespace

    # 元数据命名空间
    meta = MetaNamespace

    # 缓存管理命名空间
    cache = CacheNamespace

    # ========== 平铺 API（proxy，向后兼容）==========

    # ========== 路径核心 API 实现（13个）==========

    @classmethod
    def get_project_root(cls) -> Path:
        """获取项目根目录"""
        return cls.path.get_project_root()

    @classmethod
    def get_core_root(cls) -> Path:
        """获取 core 目录"""
        return cls.path.get_core_root()

    @classmethod
    def get_userspace_root(cls) -> Path:
        """获取 userspace 目录"""
        return cls.path.get_userspace_root()

    @classmethod
    def get_extensions_root(cls) -> Path:
        """获取 extensions 目录"""
        return cls.path.get_extensions_root()

    @classmethod
    def get_system_root(cls) -> Path:
        """获取 system 目录"""
        return cls.path.get_system_root()

    @classmethod
    def get_default_config_root(cls) -> Path:
        """获取默认配置目录"""
        return cls.path.get_default_config_root()

    @classmethod
    def get_user_config_root(cls) -> Path:
        """获取用户配置目录"""
        return cls.path.get_user_config_root()

    @classmethod
    def get_system_db_directory(cls) -> Path:
        """获取系统数据库目录"""
        return cls.path.get_system_db_directory()

    @classmethod
    def get_backup_directory(cls) -> Path:
        """获取备份目录"""
        return cls.path.get_backup_directory()

    @classmethod
    def get_updater_directory(cls) -> Path:
        """获取 updater 目录"""
        return cls.path.get_updater_directory()

    @classmethod
    def get_userspace_tmp_directory(cls) -> Path:
        """获取临时目录"""
        return cls.path.get_userspace_tmp_directory()

    @classmethod
    def get_strategies_root(cls) -> Path:
        """获取策略根目录"""
        return cls.path.get_strategies_root()

    @classmethod
    def get_tags_root(cls) -> Path:
        """获取 Tag 根目录"""
        return cls.path.get_tags_root()

    @classmethod
    def get_strategy_directory(cls, strategy_name: str) -> Path:
        """获取指定策略的目录"""
        return cls.path.get_strategy_directory(strategy_name)

    @classmethod
    def get_tag_directory(cls, tag_name: str) -> Path:
        """获取指定 Tag scenario 的目录"""
        return cls.path.get_tag_scenario_directory(tag_name)

    # ========== 策略路径 API 实现（5个）==========

    @classmethod
    def get_strategy_directory_simulation_price(cls, strategy_name: str) -> Path:
        """获取策略模拟价格目录"""
        return cls.path.get_strategy_directory_simulation_price(strategy_name)

    @classmethod
    def get_strategy_directory_simulation_capital(cls, strategy_name: str) -> Path:
        """获取策略模拟资金目录"""
        return cls.path.get_strategy_directory_simulation_capital(strategy_name)

    @classmethod
    def get_strategy_directory_simulation_portfolio(cls, strategy_name: str) -> Path:
        """获取策略模拟组合目录"""
        return cls.path.get_strategy_directory_simulation_portfolio(strategy_name)

    @classmethod
    def get_strategy_directory_simulation_enum(cls, strategy_name: str) -> Path:
        """获取策略模拟枚举目录"""
        return cls.path.get_strategy_directory_simulation_enum(strategy_name)

    @classmethod
    def get_strategy_scan_results_directory(cls, strategy_name: str) -> Path:
        """获取策略扫描结果目录"""
        return cls.path.get_strategy_scan_results_directory(strategy_name)

    @classmethod
    def get_tag_scenario_directory(cls, scenario_name: str) -> Path:
        """获取 Tag scenario 目录"""
        return cls.path.get_tag_scenario_directory(scenario_name)

    # ========== 扩展路径 API 实现（7个）==========

    @classmethod
    def get_extensions_tables_directory(cls) -> Path:
        """获取扩展表目录"""
        return cls.path.get_extensions_tables_directory()

    @classmethod
    def get_adapters_directory(cls) -> Path:
        """获取 adapters 目录"""
        return cls.path.get_adapters_directory()

    @classmethod
    def get_data_source_handler_directory(cls, handler_name: str) -> Path:
        """获取数据源处理器目录"""
        return cls.path.get_data_source_handler_directory(handler_name)

    @classmethod
    def get_data_source_handlers_directory(cls) -> Path:
        """获取数据源处理器根目录"""
        return cls.path.get_data_source_handlers_directory()

    @classmethod
    def get_data_source_providers_directory(cls) -> Path:
        """获取数据源 providers 根目录"""
        return cls.path.get_data_source_providers_directory()

    @classmethod
    def get_data_source_provider_directory(cls, provider_name: str) -> Path:
        """获取指定数据源 provider 的目录"""
        return cls.path.get_data_source_provider_directory(provider_name)

    @classmethod
    def get_data_source_mapping_path(cls) -> Path:
        """获取数据源映射路径"""
        return cls.path.get_data_source_mapping_path()

    @classmethod
    def get_data_contract_root(cls) -> Path:
        """获取 Data Contract 根目录"""
        return cls.path.get_data_contract_root()

    @classmethod
    def get_data_contract_mapping_path(cls) -> Path:
        """获取数据契约映射路径"""
        return cls.path.get_data_contract_mapping_path()

    @classmethod
    def get_userspace_ntq_directory(cls) -> Path:
        """获取 userspace NTQ 目录"""
        return cls.path.get_userspace_ntq_directory()

    # ========== 元数据核心 API 实现（2个）==========
    @classmethod
    def core_version(cls) -> Optional[str]:
        """获取 core 版本号"""
        return cls.meta.core_version()

    @classmethod
    def core_info(cls) -> Optional[Dict[str, Any]]:
        """获取 core meta 信息"""
        return cls.meta.core_info()

    # ========== 缓存管理 API 实现（1个）==========

    @classmethod
    def clear_userspace_cache(cls) -> None:
        """清理 userspace 路径缓存"""
        cls.cache.clear_userspace_cache()

    # ========== 策略路径扩展 API 实现（8个）==========

    @classmethod
    def get_strategy_settings_path(cls, strategy_name: str) -> Path:
        """获取策略配置文件路径"""
        return cls.path.get_strategy_settings_path(strategy_name)

    @classmethod
    def get_strategy_results_directory(cls, strategy_name: str) -> Path:
        """获取策略结果目录"""
        return cls.path.get_strategy_results_directory(strategy_name)

    @classmethod
    def get_strategy_simulation_price_directory(cls, strategy_name: str) -> Path:
        """获取策略模拟价格目录"""
        return cls.path.get_strategy_simulation_price_directory(strategy_name)

    @classmethod
    def get_strategy_simulation_capital_directory(cls, strategy_name: str) -> Path:
        """获取策略模拟资金目录"""
        return cls.path.get_strategy_simulation_capital_directory(strategy_name)

    @classmethod
    def get_strategy_simulation_portfolio_directory(cls, strategy_name: str) -> Path:
        """获取策略模拟组合目录"""
        return cls.path.get_strategy_simulation_portfolio_directory(strategy_name)

    @classmethod
    def get_strategy_simulation_enum_directory(cls, strategy_name: str) -> Path:
        """获取策略模拟枚举目录"""
        return cls.path.get_strategy_simulation_enum_directory(strategy_name)

    @classmethod
    def get_strategy_scan_results_directory(cls, strategy_name: str) -> Path:
        """获取策略扫描结果目录"""
        return cls.path.get_strategy_scan_results_directory(strategy_name)

    @classmethod
    def get_tag_scenario_settings_path(cls, scenario_name: str) -> Path:
        """获取 Tag scenario 配置文件路径"""
        return cls.path.get_tag_scenario_settings_path(scenario_name)

    @classmethod
    def get_tag_scenario_worker_path(cls, scenario_name: str) -> Path:
        """获取 Tag scenario worker 文件路径"""
        return cls.path.get_tag_scenario_worker_path(scenario_name)

    # ========== 扩展路径补充 API 实现（2个）==========

    @classmethod
    def get_data_source_root(cls) -> Path:
        """获取数据源根目录"""
        return cls.path.get_data_source_root()

    @classmethod
    def get_data_contract_loaders_directory(cls) -> Path:
        """获取数据契约加载器目录"""
        return cls.path.get_data_contract_loaders_directory()