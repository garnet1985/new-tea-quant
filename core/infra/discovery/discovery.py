"""Discovery facade — public entry for file / discover / class_discovery namespace API."""

from .core.namespaces import FileNamespace, DiscoverNamespace, ClassDiscoveryNamespace


class Discovery:
    """Discovery module facade."""

    # namespace instances (static attributes)
    file = FileNamespace()
    discover = DiscoverNamespace()
    class_discovery = ClassDiscoveryNamespace()


__all__ = ['Discovery']