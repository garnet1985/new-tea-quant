"""旧 tag.settings 包。

MIGRATED (settings normalize) →
    ``core.modules.tag.core.engines.shared.tag_settings.TagSettings``

本包仍导出旧 freestanding helpers，供未迁移调用方使用。
AUDIT: discovery / engines 切走后收紧 exports 或删除本包。
"""

from .worker_profile import (
    profile_tag_entity_based_config,
    profile_tag_slice_based_config,
)
from .normalize import normalize_tag_settings, declaration_data_key

__all__ = [
    "normalize_tag_settings",
    "declaration_data_key",
    "profile_tag_entity_based_config",
    "profile_tag_slice_based_config",
]
