"""跨模块契约类型（发现配置 / 结果等）。

推荐::

    from core.infra.discovery import Discovery
    from core.infra.discovery.contracts import DiscoveryConfig, DiscoveryResult
"""

from __future__ import annotations

from core.infra.discovery.core.class_discovery import (
    ClassDiscovery,
    DiscoveryConfig,
    DiscoveryResult,
)
from core.infra.discovery.core.file_discovery import FileDiscoveryConfig

__all__ = [
    "DiscoveryConfig",
    "DiscoveryResult",
    "ClassDiscovery",
    "FileDiscoveryConfig",
]
