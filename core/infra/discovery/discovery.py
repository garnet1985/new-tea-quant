"""Discovery 门面（Facade）— infra.discovery 对外统一入口类。

实现位于 ``core/``；跨模块契约类型见 ``contracts.py``。
"""

from .core.namespaces import (
    ClassDiscoveryNamespace,
    DiscoverNamespace,
    FileNamespace,
)


class Discovery:
    """New Tea Quant（NTQ）发现门面类（Facade：对外统一入口）。"""

    file = FileNamespace()
    discover = DiscoverNamespace()
    class_discovery = ClassDiscoveryNamespace()


__all__ = ["Discovery"]
