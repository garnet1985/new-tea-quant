"""Tag visualization implementer (T1-07)."""

from __future__ import annotations

from typing import Any, Dict, Optional

from core.modules.tag import Tag


class TagVisualizationImplementer:
    def lazy_load(self) -> "TagVisualizationImplementer":
        return self

    def fetch(self, tag_key: str, entity_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        return Tag.fetch_visualization(tag_key, entity_id)


impl = TagVisualizationImplementer()
