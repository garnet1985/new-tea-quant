"""
Project Context Manager - 项目上下文管理器

职责：Facade 模式，组合 PathManager、DiscoveryManager、ConfigManager、FileManager 提供统一入口

设计原则：
- 对外唯一入口：用户只通过 ProjectContext 访问功能
- 实现抽象接口：实现 ProjectContextAPI 定义的所有API
- 内部实现私有：PathManager等不对外暴露

改动记录：
- v0.4.0: 改为类方法（@classmethod），不需要实例化，调用更简洁
"""
import json
from pathlib import Path
from typing import Optional, Dict, Any, List

from .api import ProjectContextAPI
from .path_manager import PathManager
from .file_manager import FileManager
from .config_manager import ConfigManager
from .discovery_manager import DiscoveryManager


class ProjectContext(ProjectContextAPI):
    """
    Project Context Manager - 对外唯一入口
    
    实现ProjectContextAPI，组合内部Manager提供功能
    
    v0.4.0改动：改为类方法，调用更简洁：
        # 之前：ctx = ProjectContext(); ProjectContext.get_project_root()
        # 现在：ProjectContext.get_project_root()
    
    使用示例：
        # 用户代码（唯一入口）
        root = ProjectContext.get_project_root()
        core_dir = ProjectContext.get_core_root()
        settings = ProjectContext.load_core_config("logging")
        strategies = ProjectContext.discover_strategies()
    
    注意：
        - 所有方法都是类方法（不需要实例化）
        - 内部Manager（PathManager等）不对外暴露
        - API契约由 ProjectContextAPI 定义
    """
    
    # ========== 路径核心 API 实现（7个）==========

    @classmethod
    def get_project_root(cls) -> Path:
        """获取项目根目录"""
        return PathManager.get_project_root()

    @classmethod
    def get_core_root(cls) -> Path:
        """获取 core 目录"""
        return PathManager.get_core_root()

    @classmethod
    def get_userspace_root(cls) -> Path:
        """获取 userspace 目录"""
        return PathManager.get_userspace_root()

    @classmethod
    def get_strategies_root(cls) -> Path:
        """获取策略根目录"""
        return PathManager.get_strategies_root()

    @classmethod
    def get_tags_root(cls) -> Path:
        """获取 Tag 根目录"""
        return PathManager.get_tags_root()

    @classmethod
    def get_strategy_directory(cls, strategy_name: str) -> Path:
        """获取指定策略的目录"""
        return PathManager.get_strategy_directory(strategy_name)

    @classmethod
    def get_tag_directory(cls, tag_name: str) -> Path:
        """获取指定 Tag scenario 的目录"""
        return PathManager.get_tag_scenario_directory(tag_name)

    # ========== 策略路径 API 实现（5个）==========

    @classmethod
    def get_strategy_directory_simulation_price(cls, strategy_name: str) -> Path:
        """获取策略模拟价格目录"""
        return PathManager.get_strategy_simulation_price_directory(strategy_name)

    @classmethod
    def get_strategy_directory_simulation_capital(cls, strategy_name: str) -> Path:
        """获取策略模拟资金目录"""
        return PathManager.get_strategy_simulation_capital_directory(strategy_name)

    @classmethod
    def get_strategy_directory_simulation_enum(cls, strategy_name: str) -> Path:
        """获取策略模拟枚举目录"""
        return PathManager.get_strategy_simulation_enum_directory(strategy_name)

    @classmethod
    def get_strategy_directory_scan_results(cls, strategy_name: str) -> Path:
        """获取策略扫描结果目录"""
        return PathManager.get_strategy_scan_results_directory(strategy_name)

    @classmethod
    def get_tag_scenario_directory(cls, scenario_name: str) -> Path:
        """获取 Tag scenario 目录"""
        return PathManager.get_tag_scenario_directory(scenario_name)

    # ========== 扩展路径 API 实现（7个）==========

    @classmethod
    def get_extensions_tables_directory(cls) -> Path:
        """获取扩展表目录"""
        return PathManager.get_extensions_tables_directory()

    @classmethod
    def get_adapters_directory(cls) -> Path:
        """获取 adapters 目录"""
        return PathManager.get_adapters_directory()

    @classmethod
    def get_data_source_handler_directory(cls, handler_name: str) -> Path:
        """获取数据源处理器目录"""
        return PathManager.get_data_source_handler_directory(handler_name)

    @classmethod
    def get_data_source_handlers_directory(cls) -> Path:
        """获取数据源处理器根目录"""
        return PathManager.get_data_source_handlers_directory()

    @classmethod
    def get_data_source_providers_directory(cls) -> Path:
        """获取数据源 providers 根目录"""
        return PathManager.get_data_source_providers_directory()

    @classmethod
    def get_data_source_provider_directory(cls, provider_name: str) -> Path:
        """获取指定数据源 provider 的目录"""
        return PathManager.get_data_source_provider_directory(provider_name)

    @classmethod
    def get_data_source_mapping_path(cls) -> Path:
        """获取数据源映射路径"""
        return PathManager.get_data_source_mapping_path()

    @classmethod
    def get_data_contract_root(cls) -> Path:
        """获取 Data Contract 根目录"""
        return PathManager.get_data_contract_root()

    @classmethod
    def get_data_contract_mapping_path(cls) -> Path:
        """获取数据契约映射路径"""
        return PathManager.get_data_contract_mapping_path()

    @classmethod
    def get_userspace_ntq_directory(cls) -> Path:
        """获取 userspace NTQ 目录"""
        return PathManager.get_userspace_ntq_directory()

    # ========== 配置核心 API 实现（3个）==========

    @classmethod
    def load_core_config(cls, config_name: str) -> Dict[str, Any]:
        """加载 core 配置"""
        try:
            return ConfigManager.load_core_config(config_name)
        except Exception:
            # 如果配置不存在或加载失败，返回空字典
            return {}

    @classmethod
    def load_database_config(cls, database_type: Optional[str] = None) -> Dict[str, Any]:
        """加载数据库配置"""
        return ConfigManager.load_database_config(database_type)

    @classmethod
    def load_data_config(cls) -> Dict[str, Any]:
        """加载 data.json 配置"""
        return ConfigManager.load_data_config()

    # ========== 特殊配置 API 实现（3个）==========

    @classmethod
    def get_default_start_date(cls) -> str:
        """获取 data.json 的 default_start_date 配置"""
        return ConfigManager.get_default_start_date()

    @classmethod
    def get_as_of_latest_completed_trading_date(cls) -> Optional[str]:
        """获取 data.json 的 as_of_latest_completed_trading_date 配置"""
        return ConfigManager.get_as_of_latest_completed_trading_date()

    @classmethod
    def get_use_sample_stock_list(cls) -> Optional[int]:
        """获取 data.json 的 use_sample_stock_list 配置"""
        return ConfigManager.get_use_sample_stock_list()

    # ========== 发现核心 API 实现（3个）==========

    @classmethod
    def discover_strategies(cls) -> List[str]:
        """发现所有策略"""
        strategies_root = PathManager.get_strategies_root()
        if not strategies_root.is_dir():
            return []

        strategies = []
        for path in strategies_root.iterdir():
            if path.is_dir() and not path.name.startswith('.'):
                strategies.append(path.name)

        return sorted(strategies)

    @classmethod
    def discover_tags(cls) -> List[str]:
        """发现所有 Tag scenario"""
        tags_root = PathManager.get_tags_root()
        if not tags_root.is_dir():
            return []

        tags = []
        for path in tags_root.iterdir():
            if path.is_dir() and not path.name.startswith('.'):
                tags.append(path.name)

        return sorted(tags)

    @classmethod
    def discover_configs(cls, domain: str = "") -> Dict[str, Dict[str, Any]]:
        """发现指定 domain 的所有配置（默认为根级配置）"""
        try:
            config_names = DiscoveryManager.discover_configs(domain=domain)
            configs = {}
            for config_name in config_names:
                try:
                    config = DiscoveryManager.load_overridable_config(
                        domain=domain, config_id=config_name
                    )
                    configs[config_name] = config
                except Exception:
                    # 如果加载失败，跳过该配置
                    continue
            return configs
        except Exception:
            # 如果发现失败，返回空字典
            return {}
    
    # ========== 文件核心 API 实现（2个）==========
    
    @classmethod
    def find_file(cls, filename: str, search_dir: Path, recursive: bool = True) -> Optional[Path]:
        """查找单个文件"""
        return FileManager.find_file(filename, search_dir, recursive=recursive)
    
    @classmethod
    def load_file_content(cls, path: Path, encoding: str = "utf-8") -> Optional[str]:
        """加载文件内容"""
        return FileManager.load_file_content(path, encoding=encoding)
    
    # ========== 元数据核心 API 实现（2个）==========
    
    @classmethod
    def core_version(cls) -> Optional[str]:
        """获取 core 版本号"""
        core_info = cls.core_info()
        if core_info is None:
            return None
        v = core_info.get("version")
        return str(v) if v is not None else None
    
    @classmethod
    def core_info(cls) -> Optional[Dict[str, Any]]:
        """获取 core meta 信息"""
        core_dir = PathManager.get_core_root()
        meta_file = core_dir / "core_meta.json"

        content = FileManager.load_file_content(meta_file)
        if content is not None:
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                pass

        try:
            from core.system import system_meta
            return system_meta.to_dict()
        except Exception:
            return None
    
    # ========== 缓存管理 API 实现（1个）==========
    
    @classmethod
    def clear_userspace_cache(cls) -> None:
        """清理 userspace 路径缓存"""
        PathManager.clear_userspace_cache()
    
    # ========== 补充的辅助API（不对外暴露）==========
    
    @classmethod
    def load_python(cls, path: Path, var_name: str) -> Optional[Dict[str, Any]]:
        """
        加载Python配置文件（辅助方法）
        
        注意：此方法可能不对外暴露，仅供内部使用
        """
        return ConfigManager.parse_python_config(path, var_name)