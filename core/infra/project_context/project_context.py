"""Project Context facade — public entry for project path / config / meta / cache / discovery."""

from .core.namespaces import PathNamespace, MetaNamespace, CacheNamespace, ConfigNamespace, DiscoveryNamespace


class ProjectContext:
    """ProjectContext module facade."""

    # namespace instances (static attributes)
    path = PathNamespace()
    meta = MetaNamespace()
    cache = CacheNamespace()
    config = ConfigNamespace()
    discovery = DiscoveryNamespace()


__all__ = ['ProjectContext']