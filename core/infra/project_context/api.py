"""
Project Context API - 对外暴露API

只暴露namespace API，不暴露class和便捷函数。

使用方式：
    from core.infra.project_context import api

    # 路径操作
    root = api.path.get_project_root()
    core = api.path.get_core_root()

    # 元数据
    version = api.meta.core_version()
"""

from .core.namespaces import PathNamespace, MetaNamespace, CacheNamespace

# 创建namespace实例
path = PathNamespace()
meta = MetaNamespace()
cache = CacheNamespace()

# 只暴露namespace，不暴露其他任何东西
__all__ = ['path', 'meta', 'cache']