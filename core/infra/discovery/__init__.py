"""Discovery（``infra.discovery``）— 文件与类发现基础设施。

公开门面::

    from core.infra.discovery import Discovery

跨模块契约类型见 ``contracts``::

    from core.infra.discovery.contracts import DiscoveryConfig, DiscoveryResult
"""

from .discovery import Discovery

__all__ = ["Discovery"]
