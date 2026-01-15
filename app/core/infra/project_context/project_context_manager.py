"""
Project Context Manager - 项目上下文管理器

职责：Facade 模式，组合 PathManager、FileManager、ConfigManager 提供统一入口。

设计原则：
- 组合 PathManager、FileManager、ConfigManager
- 提供便捷的统一 API
- 可以独立使用各个 Manager，也可以使用 Facade
"""

from .path_manager import PathManager
from .file_manager import FileManager
from .config_manager import ConfigManager


class ProjectContextManager:
    """
    项目上下文管理器 - Facade，组合三个 Manager
    
    使用示例：
        # 方式 1：使用 Facade（推荐）
        ctx = ProjectContextManager()
        core_dir = ctx.path.core()
        settings = ctx.config.load_with_defaults(default_path, user_path)
        file = ctx.file.find_file("settings.py", ctx.path.userspace())
        
        # 方式 2：独立使用（灵活）
        from app.core.infra.project_context import PathManager, FileManager, ConfigManager
        core_dir = PathManager.core()
    """
    
    def __init__(self):
        """初始化项目上下文管理器"""
        self.path = PathManager
        self.file = FileManager
        self.config = ConfigManager
