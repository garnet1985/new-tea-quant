"""
Project Context API - 对外接口定义

职责：定义所有对外API的抽象接口，确保契约稳定

设计原则：
- 单一入口点：用户只通过 ProjectContext 访问功能
- API契约明确：抽象类定义所有对外API
- 防止误用：内部Manager不对外暴露

改动记录：
- v0.4.0: 改为类方法（@classmethod），调用更简洁，不需要实例化
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any, List


class ProjectContextAPI(ABC):
    """
    Project Context API - 对外接口定义

    所有对外API在此定义，确保契约稳定。
    用户只能通过 ProjectContext 访问功能。

    v0.4.0改动：改为类方法，调用更简洁：
        # 之前：ctx = ProjectContext(); ProjectContext.get_project_root()
        # 现在：ProjectContext.get_project_root()
    """

    # ========== 路径核心 API（13个）==========

    @classmethod
    @abstractmethod
    def get_project_root(cls) -> Path:
        """获取项目根目录"""
        pass

    @classmethod
    @abstractmethod
    def get_core_root(cls) -> Path:
        """获取 core 目录"""
        pass

    @classmethod
    @abstractmethod
    def get_userspace_root(cls) -> Path:
        """获取 userspace 目录"""
        pass

    @classmethod
    @abstractmethod
    def get_extensions_root(cls) -> Path:
        """获取 extensions 目录"""
        pass

    @classmethod
    @abstractmethod
    def get_system_root(cls) -> Path:
        """获取 system 目录"""
        pass

    @classmethod
    @abstractmethod
    def get_default_config_root(cls) -> Path:
        """获取默认配置目录"""
        pass

    @classmethod
    @abstractmethod
    def get_user_config_root(cls) -> Path:
        """获取用户配置目录"""
        pass

    @classmethod
    @abstractmethod
    def get_system_db_directory(cls) -> Path:
        """获取系统数据库目录"""
        pass

    @classmethod
    @abstractmethod
    def get_backup_directory(cls) -> Path:
        """获取备份目录"""
        pass

    @classmethod
    @abstractmethod
    def get_updater_directory(cls) -> Path:
        """获取 updater 目录"""
        pass

    @classmethod
    @abstractmethod
    def get_userspace_tmp_directory(cls) -> Path:
        """获取临时目录"""
        pass

    @classmethod
    @abstractmethod
    def get_strategies_root(cls) -> Path:
        """获取策略根目录"""
        pass

    @classmethod
    @abstractmethod
    def get_tags_root(cls) -> Path:
        """获取 Tag 根目录"""
        pass

    # ========== 策略路径 API（5个）==========

    @classmethod
    @abstractmethod
    def get_strategy_directory_simulation_price(cls, strategy_name: str) -> Path:
        """获取策略模拟价格目录"""
        pass

    @classmethod
    @abstractmethod
    def get_strategy_directory_simulation_capital(cls, strategy_name: str) -> Path:
        """获取策略模拟资金目录"""
        pass

    @classmethod
    @abstractmethod
    def get_strategy_directory_simulation_enum(cls, strategy_name: str) -> Path:
        """获取策略模拟枚举目录"""
        pass

    @classmethod
    @abstractmethod
    def get_strategy_scan_results_directory(cls, strategy_name: str) -> Path:
        """获取策略扫描结果目录"""
        pass

    @classmethod
    @abstractmethod
    def get_tag_scenario_directory(cls, scenario_name: str) -> Path:
        """获取 Tag scenario 目录"""
        pass

    # ========== 扩展路径 API（10个）==========

    @classmethod
    @abstractmethod
    def get_extensions_tables_directory(cls) -> Path:
        """获取扩展表目录"""
        pass

    @classmethod
    @abstractmethod
    def get_adapters_directory(cls) -> Path:
        """获取 adapters 目录"""
        pass

    @classmethod
    @abstractmethod
    def get_data_source_handler_directory(cls, handler_name: str) -> Path:
        """获取数据源处理器目录"""
        pass

    @classmethod
    @abstractmethod
    def get_data_source_handlers_directory(cls) -> Path:
        """获取数据源处理器根目录"""
        pass

    @classmethod
    @abstractmethod
    def get_data_source_providers_directory(cls) -> Path:
        """获取数据源 providers 根目录"""
        pass

    @classmethod
    @abstractmethod
    def get_data_source_provider_directory(cls, provider_name: str) -> Path:
        """获取指定数据源 provider 的目录"""
        pass

    @classmethod
    @abstractmethod
    def get_data_source_mapping_path(cls) -> Path:
        """获取数据源映射路径"""
        pass

    @classmethod
    @abstractmethod
    def get_data_contract_root(cls) -> Path:
        """获取 Data Contract 根目录"""
        pass

    @classmethod
    @abstractmethod
    def get_data_contract_mapping_path(cls) -> Path:
        """获取数据契约映射路径"""
        pass

    @classmethod
    @abstractmethod
    def get_userspace_ntq_directory(cls) -> Path:
        """获取 userspace NTQ 目录"""
        pass

    # ========== 策略路径扩展 API（8个）==========

    @classmethod
    @abstractmethod
    def get_strategy_settings_path(cls, strategy_name: str) -> Path:
        """获取策略配置文件路径"""
        pass

    @classmethod
    @abstractmethod
    def get_strategy_results_directory(cls, strategy_name: str) -> Path:
        """获取策略结果目录"""
        pass

    @classmethod
    @abstractmethod
    def get_strategy_simulation_price_directory(cls, strategy_name: str) -> Path:
        """获取策略模拟价格目录"""
        pass

    @classmethod
    @abstractmethod
    def get_strategy_simulation_capital_directory(cls, strategy_name: str) -> Path:
        """获取策略模拟资金目录"""
        pass

    @classmethod
    @abstractmethod
    def get_strategy_simulation_enum_directory(cls, strategy_name: str) -> Path:
        """获取策略模拟枚举目录"""
        pass

    @classmethod
    @abstractmethod
    def get_strategy_scan_results_directory(cls, strategy_name: str) -> Path:
        """获取策略扫描结果目录"""
        pass

    @classmethod
    @abstractmethod
    def get_tag_scenario_settings_path(cls, scenario_name: str) -> Path:
        """获取 Tag scenario 配置文件路径"""
        pass

    @classmethod
    @abstractmethod
    def get_tag_scenario_worker_path(cls, scenario_name: str) -> Path:
        """获取 Tag scenario worker 文件路径"""
        pass

    # ========== 扩展路径补充 API（2个）==========

    @classmethod
    @abstractmethod
    def get_data_source_root(cls) -> Path:
        """获取数据源根目录"""
        pass

    @classmethod
    @abstractmethod
    def get_data_contract_loaders_directory(cls) -> Path:
        """获取数据契约加载器目录"""
        pass

    # ========== 元数据核心 API（2个）==========

    @classmethod
    @abstractmethod
    def core_version(cls) -> Optional[str]:
        """获取 core 版本号"""
        pass

    @classmethod
    @abstractmethod
    def core_info(cls) -> Optional[Dict[str, Any]]:
        """获取 core meta 信息"""
        pass

    # ========== 缓存管理 API（1个）==========

    @classmethod
    @abstractmethod
    def clear_userspace_cache(cls) -> None:
        """清理 userspace 路径缓存"""
        pass