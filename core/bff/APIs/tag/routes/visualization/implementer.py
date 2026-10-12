"""Tag visualization implementer (T1-07)."""

from __future__ import annotations

from typing import Any, Dict, Optional


class TagVisualizationImplementer:
    def __init__(self) -> None:
        self._TagVisualization = None

    def lazy_load(self) -> "TagVisualizationImplementer":
        if self._TagVisualization is None:
            from core.bff.APIs.tag.helpers.tag_visualization import TagVisualization

            self._TagVisualization = TagVisualization
        return self

    def fetch(self, tag_key: str, entity_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        assert self._TagVisualization is not None
        return self._TagVisualization.fetch(tag_key, entity_id)


impl = TagVisualizationImplementer()
