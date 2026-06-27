"""命名空间 API - 提供清晰的命名空间访问方式"""
from typing import Dict, Any, Optional
from pathlib import Path
import json


class PathNamespace:
    """路径操作命名空间"""

    @staticmethod
    def get_project_root() -> Path:
        """获取项目根目录"""
        from .path_manager import PathManager
        return PathManager.get_project_root()

    @staticmethod
    def get_core_root() -> Path:
        """获取 core 目录"""
        from .path_manager import PathManager
        return PathManager.get_core_root()

    @staticmethod
    def get_userspace_root() -> Path:
        """获取 userspace 目录"""
        from .path_manager import PathManager
        return PathManager.get_userspace_root()

    @staticmethod
    def get_extensions_root() -> Path:
        """获取 extensions 目录"""
        from .path_manager import PathManager
        return PathManager.get_extensions_root()

    @staticmethod
    def get_system_root() -> Path:
        """获取 system 目录"""
        from .path_manager import PathManager
        return PathManager.get_system_root()

    @staticmethod
    def get_default_config_root() -> Path:
        """获取默认配置目录"""
        from .path_manager import PathManager
        return PathManager.get_default_config_root()

    @staticmethod
    def get_user_config_root() -> Path:
        """获取用户配置目录"""
        from .path_manager import PathManager
        return PathManager.get_user_config_root()

    @staticmethod
    def get_system_db_directory() -> Path:
        """获取系统数据库目录"""
        from .path_manager import PathManager
        return PathManager.get_system_db_directory()

    @staticmethod
    def get_backup_directory() -> Path:
        """获取备份目录"""
        from .path_manager import PathManager
        return PathManager.get_backup_directory()

    @staticmethod
    def get_updater_directory() -> Path:
        """获取 updater 目录"""
        from .path_manager import PathManager
        return PathManager.get_updater_directory()

    @staticmethod
    def get_userspace_tmp_directory() -> Path:
        """获取临时目录"""
        from .path_manager import PathManager
        return PathManager.get_userspace_tmp_directory()

    @staticmethod
    def get_strategies_root() -> Path:
        """获取策略根目录"""
        from .path_manager import PathManager
        return PathManager.get_strategies_root()

    @staticmethod
    def get_tags_root() -> Path:
        """获取 Tag 根目录"""
        from .path_manager import PathManager
        return PathManager.get_tags_root()

    @staticmethod
    def get_data_source_root() -> Path:
        """获取数据源根目录"""
        from .path_manager import PathManager
        return PathManager.get_data_source_root()

    # ========== 策略和Tag路径（额外方法）==========

    @staticmethod
    def get_strategy_directory(strategy_name: str) -> Path:
        """获取指定策略的目录"""
        from .path_manager import PathManager
        return PathManager.get_strategy_directory(strategy_name)

    @staticmethod
    def get_tag_directory(tag_name: str) -> Path:
        """获取指定 Tag scenario 的目录"""
        from .path_manager import PathManager
        return PathManager.get_tag_scenario_directory(tag_name)

    # ========== 策略路径 API ==========

    @staticmethod
    def get_strategy_directory_simulation_price(strategy_name: str) -> Path:
        """获取策略模拟价格目录"""
        from .path_manager import PathManager
        return PathManager.get_strategy_simulation_price_directory(strategy_name)

    @staticmethod
    def get_strategy_directory_simulation_capital(strategy_name: str) -> Path:
        """获取策略模拟资金目录"""
        from .path_manager import PathManager
        return PathManager.get_strategy_simulation_capital_directory(strategy_name)

    @staticmethod
    def get_strategy_directory_simulation_enum(strategy_name: str) -> Path:
        """获取策略模拟枚举目录"""
        from .path_manager import PathManager
        return PathManager.get_strategy_simulation_enum_directory(strategy_name)

    @staticmethod
    def get_strategy_directory_scan_results(strategy_name: str) -> Path:
        """获取策略扫描结果目录"""
        from .path_manager import PathManager
        return PathManager.get_strategy_scan_results_directory(strategy_name)

    @staticmethod
    def get_tag_scenario_directory(scenario_name: str) -> Path:
        """获取 Tag scenario 目录"""
        from .path_manager import PathManager
        return PathManager.get_tag_scenario_directory(scenario_name)

    # ========== 扩展路径 API ==========

    @staticmethod
    def get_extensions_tables_directory() -> Path:
        """获取扩展表目录"""
        from .path_manager import PathManager
        return PathManager.get_extensions_tables_directory()

    @staticmethod
    def get_adapters_directory() -> Path:
        """获取 adapters 目录"""
        from .path_manager import PathManager
        return PathManager.get_adapters_directory()

    @staticmethod
    def get_data_source_handler_directory(handler_name: str) -> Path:
        """获取数据源处理器目录"""
        from .path_manager import PathManager
        return PathManager.get_data_source_handler_directory(handler_name)

    @staticmethod
    def get_data_source_handlers_directory() -> Path:
        """获取数据源处理器根目录"""
        from .path_manager import PathManager
        return PathManager.get_data_source_handlers_directory()

    @staticmethod
    def get_data_source_providers_directory() -> Path:
        """获取数据源 providers 根目录"""
        from .path_manager import PathManager
        return PathManager.get_data_source_providers_directory()

    @staticmethod
    def get_data_source_provider_directory(provider_name: str) -> Path:
        """获取指定数据源 provider 的目录"""
        from .path_manager import PathManager
        return PathManager.get_data_source_provider_directory(provider_name)

    @staticmethod
    def get_data_source_mapping_path() -> Path:
        """获取数据源映射路径"""
        from .path_manager import PathManager
        return PathManager.get_data_source_mapping_path()

    @staticmethod
    def get_data_contract_root() -> Path:
        """获取 Data Contract 根目录"""
        from .path_manager import PathManager
        return PathManager.get_data_contract_root()

    @staticmethod
    def get_data_contract_mapping_path() -> Path:
        """获取数据契约映射路径"""
        from .path_manager import PathManager
        return PathManager.get_data_contract_mapping_path()

    @staticmethod
    def get_userspace_ntq_directory() -> Path:
        """获取 userspace NTQ 目录"""
        from .path_manager import PathManager
        return PathManager.get_userspace_ntq_directory()

    # ========== 策略路径扩展 API ==========

    @staticmethod
    def get_strategy_settings_path(strategy_name: str) -> Path:
        """获取策略配置文件路径"""
        from .path_manager import PathManager
        return PathManager.get_strategy_settings_path(strategy_name)

    @staticmethod
    def get_strategy_results_directory(strategy_name: str) -> Path:
        """获取策略结果目录"""
        from .path_manager import PathManager
        return PathManager.get_strategy_results_directory(strategy_name)

    @staticmethod
    def get_strategy_simulation_price_directory(strategy_name: str) -> Path:
        """获取策略模拟价格目录"""
        from .path_manager import PathManager
        return PathManager.get_strategy_simulation_price_directory(strategy_name)

    @staticmethod
    def get_strategy_simulation_capital_directory(strategy_name: str) -> Path:
        """获取策略模拟资金目录"""
        from .path_manager import PathManager
        return PathManager.get_strategy_simulation_capital_directory(strategy_name)

    @staticmethod
    def get_strategy_simulation_enum_directory(strategy_name: str) -> Path:
        """获取策略模拟枚举目录"""
        from .path_manager import PathManager
        return PathManager.get_strategy_simulation_enum_directory(strategy_name)

    @staticmethod
    def get_strategy_scan_results_directory(strategy_name: str) -> Path:
        """获取策略扫描结果目录"""
        from .path_manager import PathManager
        return PathManager.get_strategy_scan_results_directory(strategy_name)

    @staticmethod
    def get_tag_scenario_settings_path(scenario_name: str) -> Path:
        """获取 Tag scenario 配置文件路径"""
        from .path_manager import PathManager
        return PathManager.get_tag_scenario_settings_path(scenario_name)

    @staticmethod
    def get_tag_scenario_worker_path(scenario_name: str) -> Path:
        """获取 Tag scenario worker 文件路径"""
        from .path_manager import PathManager
        return PathManager.get_tag_scenario_worker_path(scenario_name)

    # ========== 扩展路径补充 API ==========

    @staticmethod
    def get_data_contract_loaders_directory() -> Path:
        """获取数据契约加载器目录"""
        from .path_manager import PathManager
        return PathManager.get_data_contract_loaders_directory()


class MetaNamespace:
    """元数据操作命名空间"""

    @staticmethod
    def core_version() -> Optional[str]:
        """获取 core 版本号"""
        core_info = MetaNamespace.core_info()
        if core_info is None:
            return None
        v = core_info.get("version")
        return str(v) if v is not None else None

    @staticmethod
    def core_info() -> Optional[Dict[str, Any]]:
        """获取 core meta 信息"""
        from .path_manager import PathManager
        core_dir = PathManager.get_core_root()
        meta_file = core_dir / "core_meta.json"

        # 直接读取文件
        if meta_file.exists():
            try:
                with meta_file.open('r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

        # 尝试从 system_meta 加载
        try:
            from core.system import system_meta
            return system_meta.to_dict()
        except Exception:
            return None


class CacheNamespace:
    """缓存管理命名空间"""

    @staticmethod
    def clear_userspace_cache() -> None:
        """清理 userspace 路径缓存"""
        from .path_manager import PathManager
        PathManager.clear_userspace_cache()