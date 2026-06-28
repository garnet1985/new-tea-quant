"""
Project Context Module - 项目上下文管理

使用方式：
    from core.infra.project_context import ProjectContext
    
    # 路径操作
    root = ProjectContext.path.get_project_root()
    core = ProjectContext.path.get_core_root()
"""

from .project_context import ProjectContext
from .core.discovery_manager import OverridableConfigNotFoundError

__all__ = ['ProjectContext', 'OverridableConfigNotFoundError']