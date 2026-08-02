"""命名空间 API - 提供清晰的命名空间访问方式"""
from typing import Dict, Any, Optional, Set, List, Callable
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
    def get_strategy_directory_simulation_portfolio(strategy_name: str) -> Path:
        """获取策略模拟组合目录"""
        from .path_manager import PathManager
        return PathManager.get_strategy_simulation_portfolio_directory(strategy_name)

    @staticmethod
    def get_strategy_directory_simulation_enum(strategy_name: str) -> Path:
        """获取策略模拟枚举目录"""
        from .path_manager import PathManager
        return PathManager.get_strategy_simulation_enum_directory(strategy_name)

    @staticmethod
    def get_strategy_scan_results_directory(strategy_name: str) -> Path:
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
    def get_strategy_simulation_portfolio_directory(strategy_name: str) -> Path:
        """获取策略模拟组合目录"""
        from .path_manager import PathManager
        return PathManager.get_strategy_simulation_portfolio_directory(strategy_name)

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


class ConfigNamespace:
    """配置管理命名空间"""

    @staticmethod
    def get_as_of_latest_completed_trading_date() -> Optional[str]:
        """
        data.json ``as_of_latest_completed_trading_date``（全系统 as-of 权威）。

        配置后 ``CalendarService.get_latest_completed_trading_date`` 直接返回该值。
        """
        from .config_manager import ConfigManager
        return ConfigManager.get_as_of_latest_completed_trading_date()

    @staticmethod
    def get_default_start_date() -> str:
        """
        获取默认开始日期

        Returns:
            默认开始日期字符串（格式：YYYYMMDD）
        """
        from .config_manager import ConfigManager
        return ConfigManager.get_default_start_date()

    @staticmethod
    def get_default_market_profile_key() -> str:
        """
        ``data.json`` → ``default_market_profile_key``（全系统默认市场 profile id）。
        """
        from .config_manager import ConfigManager
        return ConfigManager.get_default_market_profile_key()

    @staticmethod
    def get_use_sample_stock_list() -> Optional[int]:
        """
        开发样本股票池规模（``core/modules/data_source/dev/stock_pool/stratified_N.csv``）。

        - 正整数 ``N`` → 使用 ``stratified_N.csv``
        - 未配置 / 空 / 非正数 → 全市场
        """
        from .config_manager import ConfigManager
        return ConfigManager.get_use_sample_stock_list()

    @staticmethod
    def load_database_config(database_type: str = None) -> Dict[str, Any]:
        """
        加载数据库配置（自动合并 userspace 配置）

        加载流程：
        1. 加载 core/default_config/database/common.json（公用配置，包含 database_type）
        2. 加载 core/default_config/database/{database_type}.json（数据库专用配置）
        3. 合并：database_type 配置覆盖 common 配置
        4. 加载 userspace/config/database/common.json（用户公用配置，如果存在）
        5. 加载 userspace/config/database/{database_type}.json（用户数据库配置，如果存在）
        6. 深度合并：用户配置覆盖默认配置
        7. 环境变量覆盖（最高优先级）

        Args:
            database_type: 数据库类型（'postgresql', 'mysql'）
                          如果为 None，从配置文件中获取

        Returns:
            合并后的数据库配置字典，格式：
            {
                'database_type': 'postgresql',
                'postgresql': {...},  # 或 'mysql': {...}
                'batch_write': {...}
            }
        """
        from .config_manager import ConfigManager
        return ConfigManager.load_database_config(database_type)

    @staticmethod
    def load_core_config(
        config_name: str,
        deep_merge_fields: Set[str] = None,
        override_fields: Set[str] = None
    ) -> Dict[str, Any]:
        """
        加载核心配置（自动合并 userspace 配置）

        加载流程：
        1. 加载 core/default_config/{config_name}.json（默认配置）
        2. 加载 userspace/config/{config_name}.json（用户配置，如果存在）
        3. 深度合并：用户配置覆盖默认配置

        Args:
            config_name: 配置文件名（不含 .json 后缀）
            deep_merge_fields: 需要深度合并的字段名集合
            override_fields: 需要完全覆盖的字段名集合

        Returns:
            合并后的配置字典
        """
        from .config_manager import ConfigManager
        return ConfigManager.load_core_config(
            config_name,
            deep_merge_fields=deep_merge_fields,
            override_fields=override_fields
        )

    @staticmethod
    def load_data_config() -> Dict[str, Any]:
        """
        加载数据配置（合并后的完整配置）

        Returns:
            数据配置字典，包含 default_start_date, decimal_places 等
        """
        from .config_manager import ConfigManager
        return ConfigManager.load_data_config()

    @staticmethod
    def load_benchmark_stock_index_list() -> List[Dict[str, Any]]:
        """
        获取全局基准股票指数列表（benchmark_stock_index_list）。

        - 默认值来自 core/default_config/data.json；
        - 用户可以在 userspace/config/data.json 中覆盖或扩展该列表，
          合并逻辑由 ConfigManager.load_core_config 负责。

        Returns:
            基准股票指数列表，包含 id, name, description, type 等字段
        """
        from .config_manager import ConfigManager
        return ConfigManager.load_benchmark_stock_index_list()

    @staticmethod
    def merge_market_profile_dicts(
        core: Dict[str, Any],
        user: Dict[str, Any],
    ) -> Dict[str, Any]:
        """合并市场 profile 配置（供 discovery.load_overridable_config 的 merge_fn）。"""
        from .config_merge_policies import merge_market_profile_dicts
        return merge_market_profile_dicts(core, user)


class DiscoveryNamespace:
    """配置发现命名空间"""

    @staticmethod
    def discover_configs(domain: str = "", *, pattern: str = "*.json") -> List[str]:
        """
        扫描 core / userspace 下指定 domain 的 JSON 配置 id（无后缀），并集排序。

        Args:
            domain: 配置域（如 "markets", "data_source" 等）
            pattern: 文件匹配模式（默认 "*.json"）

        Returns:
            配置 ID 列表（排序后）
        """
        from .discovery_manager import DiscoveryManager
        return DiscoveryManager.discover_configs(domain, pattern=pattern)

    @staticmethod
    def load_overridable_config(
        domain: str,
        config_id: str,
        *,
        merge_fn: Optional[Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]] = None,
        deep_merge_fields: Optional[Set[str]] = None,
        override_fields: Optional[Set[str]] = None,
        file_type: str = "json",
    ) -> Dict[str, Any]:
        """
        加载可覆盖配置。

        Args:
            domain: 配置域（如 "markets", "data_source" 等）
            config_id: 配置 ID（如 "china_a_stock"）
            merge_fn: 自定义合并函数（可选）
            deep_merge_fields: 需要深度合并的字段名集合（可选）
            override_fields: 需要完全覆盖的字段名集合（可选）
            file_type: 文件类型（默认 "json"）

        Returns:
            合并后的配置字典

        Raises:
            OverridableConfigNotFoundError: 当 core 和 userspace 均未找到有效配置时
        """
        from .discovery_manager import DiscoveryManager
        return DiscoveryManager.load_overridable_config(
            domain,
            config_id,
            merge_fn=merge_fn,
            deep_merge_fields=deep_merge_fields,
            override_fields=override_fields,
            file_type=file_type,
        )