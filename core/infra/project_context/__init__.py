"""
Project Management Module - 项目管理模块

提供项目路径、配置发现、配置合并的统一接口。

架构：
- PathManager: 路径管理（提供常用路径的快捷访问）
- DiscoveryManager: 约定目录下的配置发现与可覆盖加载
- ConfigManager: 配置读取与合并（已知路径或专项加载器）
- FileManager: 文件 I/O 原语（查找、读取、目录）
- ProjectContextManager: Facade，组合上述 Manager
"""

from .project_context_manager import ProjectContextManager
from .path_manager import EXTENSIONS_MODULE_PREFIX, PathManager, extensions_module
from .file_manager import FileManager
from .config_manager import ConfigManager
from .discovery_manager import (
    DiscoveredConfig,
    DiscoveryManager,
    OverridableConfigNotFoundError,
)
from .config_merge_policies import merge_market_profile_dicts

__all__ = [
    "ProjectContextManager",
    "PathManager",
    "EXTENSIONS_MODULE_PREFIX",
    "extensions_module",
    "DiscoveryManager",
    "DiscoveredConfig",
    "OverridableConfigNotFoundError",
    "ConfigManager",
    "FileManager",
    "merge_market_profile_dicts",
]
