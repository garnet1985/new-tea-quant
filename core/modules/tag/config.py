"""
Tag 系统路径配置。

MIGRATED 调用方请优先用 ``PathManager.get_tags_root()``。
本类保留给少数仍引用 ``get_scenarios_root`` 的旧入口。
"""

from pathlib import Path

from core.infra.project_context import ProjectContext


class TagPaths:
    """Tag scenarios 根路径。"""

    @classmethod
    def scenarios_root(cls) -> Path:
        return ProjectContext.path.get_tags_root()


# AUDIT: 兼容旧 ``from core.modules.tag.config import get_scenarios_root``
def get_scenarios_root() -> Path:
    return TagPaths.scenarios_root()


__all__ = ["TagPaths"]
