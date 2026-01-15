"""
Project Management Module - 项目管理模块

提供项目路径、文件操作和配置管理的统一接口。

架构：
- PathManager: 路径管理（提供常用路径的快捷访问）
- FileManager: 文件管理（文件查找、读取等操作）
- ConfigManager: 配置管理（默认配置和用户配置的合并）
- ProjectContextManager: Facade，组合三个 Manager 提供统一入口

使用示例：
    from app.core.infra.project_context import ProjectContextManager
    
    ctx = ProjectContextManager()
    core_dir = ctx.path.core()
    settings = ctx.config.load_with_defaults(default_path, user_path)
"""

from .project_context_manager import ProjectContextManager
from .path_manager import PathManager
from .file_manager import FileManager
from .config_manager import ConfigManager

__all__ = [
    'ProjectContextManager',
    'PathManager',
    'FileManager',
    'ConfigManager',
]
