"""
MIGRATED → ``core.modules.tag.core.services.discovery``

AUDIT: 待 TagManager / CLI 切走后删除本包。
"""

from core.modules.tag.services.discovery.discovery import DiscoveredTag, TagDiscoveryHelper

__all__ = ["DiscoveredTag", "TagDiscoveryHelper"]
