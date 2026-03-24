"""
Project Context Manager - 项目上下文管理器

职责：Facade 模式，组合 PathManager、FileManager、ConfigManager 提供统一入口。

设计原则：
- 组合 PathManager、FileManager、ConfigManager
- 提供便捷的统一 API
- 可以独立使用各个 Manager，也可以使用 Facade
"""

import json
from typing import Optional, Dict, Any
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
        meta = ctx.core_info()  # 获取 core meta 信息
        
        # 方式 2：独立使用（灵活）
        from core.infra.project_context import PathManager, FileManager, ConfigManager
        core_dir = PathManager.core()
    """
    
    def __init__(self):
        """初始化项目上下文管理器"""
        self.path = PathManager
        self.file = FileManager
        self.config = ConfigManager
    
    def core_info(self) -> Optional[Dict[str, Any]]:
        """
        获取 core meta 信息

        优先读取 core/core_meta.json（若存在）；否则使用 core.system.SystemMeta。
        """
        core_dir = PathManager.core()
        meta_file = core_dir / "core_meta.json"

        content = FileManager.read_file(meta_file)
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

    def core_version(self) -> Optional[str]:
        """
        获取 core 版本号（与 core_info 同源）。
        """
        core_info = self.core_info()
        if core_info is None:
            return None
        v = core_info.get("version")
        return str(v) if v is not None else None
