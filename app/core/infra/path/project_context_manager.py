"""
Project Context Manager - 项目上下文管理器

职责：Facade 模式，组合 PathManager、FileManager、ConfigManager 提供统一入口。

设计原则：
- 组合 PathManager、FileManager、ConfigManager
- 提供便捷的统一 API
- 可以独立使用各个 Manager，也可以使用 Facade
- 单例模式或静态方法（待定）

TODO: 实现 Facade 功能
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
        from app.core.infra.path import PathManager, FileManager, ConfigManager
        core_dir = PathManager.core()
    """
    
    def __init__(self):
        """初始化项目上下文管理器"""
        self.path = PathManager
        self.file = FileManager
        self.config = ConfigManager
    
    # TODO: 可以添加一些常用的组合操作
    # def get_strategy_settings(self, strategy_name: str) -> Dict[str, Any]:
    #     """获取策略配置（自动合并默认配置和用户配置）"""
    #     default_path = self.path.core() / "modules" / "strategy" / "default_settings.json"
    #     user_path = self.path.strategy_settings(strategy_name)
    #     return self.config.load_with_defaults(default_path, user_path, file_type="py")
