"""
Project Context Manager - 项目上下文管理器

职责：Facade 模式，组合 PathManager、DiscoveryManager、ConfigManager、FileManager 提供统一入口

设计原则：
- 对外唯一入口：用户只通过 ProjectContextManager 访问功能
- 实现抽象接口：实现 ProjectContextAPI 定义的所有API
- 内部实现私有：PathManager等不对外暴露
"""
import json
from pathlib import Path
from typing import Optional, Dict, Any, List

from .api import ProjectContextAPI
from .path_manager import PathManager
from .file_manager import FileManager
from .config_manager import ConfigManager
from .discovery_manager import DiscoveryManager


class ProjectContextManager(ProjectContextAPI):
    """
    Project Context Manager - 对外唯一入口
    
    实现ProjectContextAPI，组合内部Manager提供功能
    
    使用示例：
        # 用户代码（唯一入口）
        ctx = ProjectContextManager()
        root = ctx.get_project_root()
        core_dir = ctx.get_core_root()
        settings = ctx.load_core_config("logging")
        strategies = ctx.discover_strategies()
    
    注意：
        - 所有方法都是实例方法
        - 内部Manager（PathManager等）不对外暴露
        - API契约由 ProjectContextAPI 定义
    """
    
    def __init__(self):
        """初始化项目上下文管理器"""
        # 内部Manager（私有实现，不对外暴露）
        self._path_manager = PathManager
        self._file_manager = FileManager
        self._config_manager = ConfigManager
        self._discovery_manager = DiscoveryManager
    
    # ========== 路径核心 API 实现（5个）==========
    
    def get_project_root(self) -> Path:
        """获取项目根目录"""
        return self._path_manager.get_project_root()
    
    def get_core_root(self) -> Path:
        """获取 core 目录"""
        return self._path_manager.get_core_root()
    
    def get_userspace_root(self) -> Path:
        """获取 userspace 目录"""
        return self._path_manager.get_userspace_root()
    
    def get_strategy_directory(self, strategy_name: str) -> Path:
        """获取指定策略的目录"""
        return self._path_manager.get_strategy_directory(strategy_name)
    
    def get_tag_directory(self, tag_name: str) -> Path:
        """获取指定 Tag scenario 的目录"""
        return self._path_manager.get_tag_scenario_directory(tag_name)
    
    # ========== 配置核心 API 实现（3个）==========

    def load_core_config(self, config_name: str) -> Dict[str, Any]:
        """加载 core 配置"""
        try:
            return self._config_manager.load_core_config(config_name)
        except Exception:
            # 如果配置不存在或加载失败，返回空字典
            return {}

    def load_database_config(self, database_type: Optional[str] = None) -> Dict[str, Any]:
        """加载数据库配置"""
        return self._config_manager.load_database_config(database_type)

    def load_data_config(self) -> Dict[str, Any]:
        """加载 data.json 配置"""
        return self._config_manager.load_data_config()

    # ========== 发现核心 API 实现（3个）==========

    def discover_strategies(self) -> List[str]:
        """发现所有策略"""
        strategies_root = self._path_manager.get_strategies_root()
        if not strategies_root.is_dir():
            return []

        strategies = []
        for path in strategies_root.iterdir():
            if path.is_dir() and not path.name.startswith('.'):
                strategies.append(path.name)

        return sorted(strategies)

    def discover_tags(self) -> List[str]:
        """发现所有 Tag scenario"""
        tags_root = self._path_manager.get_tags_root()
        if not tags_root.is_dir():
            return []

        tags = []
        for path in tags_root.iterdir():
            if path.is_dir() and not path.name.startswith('.'):
                tags.append(path.name)

        return sorted(tags)

    def discover_configs(self) -> Dict[str, Dict[str, Any]]:
        """发现所有 core 配置"""
        try:
            config_names = self._discovery_manager.discover_configs(domain="")
            configs = {}
            for config_name in config_names:
                try:
                    config = self._discovery_manager.load_overridable_config(
                        domain="", config_id=config_name
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
    
    def find_file(self, filename: str, search_dir: Path, recursive: bool = True) -> Optional[Path]:
        """查找单个文件"""
        return self._file_manager.find_file(filename, search_dir, recursive=recursive)
    
    def load_file_content(self, path: Path, encoding: str = "utf-8") -> Optional[str]:
        """加载文件内容"""
        return self._file_manager.load_file_content(path, encoding=encoding)
    
    # ========== 元数据核心 API 实现（2个）==========
    
    def core_version(self) -> Optional[str]:
        """获取 core 版本号"""
        core_info = self.core_info()
        if core_info is None:
            return None
        v = core_info.get("version")
        return str(v) if v is not None else None
    
    def core_info(self) -> Optional[Dict[str, Any]]:
        """获取 core meta 信息"""
        core_dir = self._path_manager.get_core_root()
        meta_file = core_dir / "core_meta.json"

        content = self._file_manager.load_file_content(meta_file)
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
    
    def clear_userspace_cache(self) -> None:
        """清理 userspace 路径缓存"""
        self._path_manager.clear_userspace_cache()