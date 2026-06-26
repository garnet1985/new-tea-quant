"""
Project Context Module - 项目上下文模块

对外唯一入口：ProjectContextManager

设计原则：
- 单一入口点：用户只通过 ProjectContextManager 访问功能
- API契约明确：ProjectContextAPI 定义所有对外API
- 防止误用：内部Manager不对外暴露

使用示例：
    # 用户代码（唯一入口）
    from core.infra.project_context import ProjectContextManager
    
    ctx = ProjectContextManager()
    root = ctx.get_project_root()
    core_dir = ctx.get_core_root()
    settings = ctx.load_core_config("logging")
    strategies = ctx.discover_strategies()
"""

from .api import ProjectContextAPI
from .project_context_manager import ProjectContextManager

__all__ = [
    "ProjectContextAPI",
    "ProjectContextManager",
]