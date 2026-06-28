"""
Project Context - 项目上下文管理

使用方式：
    from core.infra.project_context import ProjectContext
    
    # 路径操作（静态方法）
    root = ProjectContext.path.get_project_root()
    core = ProjectContext.path.get_core_root()
    
    # 配置操作（静态方法）
    as_of = ProjectContext.config.get_as_of_latest_completed_trading_date()
    start_date = ProjectContext.config.get_default_start_date()
    
    # 元数据（静态方法）
    version = ProjectContext.meta.core_version()
"""

from .core.namespaces import PathNamespace, MetaNamespace, CacheNamespace, ConfigNamespace, DiscoveryNamespace


class ProjectContext:
    """ProjectContext模块统一入口"""

    # namespace实例（静态属性）
    path = PathNamespace()
    meta = MetaNamespace()
    cache = CacheNamespace()
    config = ConfigNamespace()
    discovery = DiscoveryNamespace()