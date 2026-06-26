"""
Tag 系统全局配置

包含 Tag 系统的全局配置常量。
"""

from pathlib import Path

from core.infra.project_context import ProjectContext


# ========================================================================
# Scenarios 根目录配置
# ========================================================================

def get_scenarios_root() -> Path:
    """获取标签场景根目录"""
    return ProjectContext.get_tags_root()