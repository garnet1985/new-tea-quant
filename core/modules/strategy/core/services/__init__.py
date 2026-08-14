"""Strategy 内部服务（facade 层仅 export DiscoveryService）。"""

from .discovery import DiscoveryService

__all__ = ["DiscoveryService"]
