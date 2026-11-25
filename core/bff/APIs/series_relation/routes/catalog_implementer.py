"""Series relation catalog implementer."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple


class SeriesRelationCatalogImplementer:
    def __init__(self) -> None:
        self._Scenes = None

    def lazy_load(self) -> "SeriesRelationCatalogImplementer":
        if self._Scenes is None:
            from core.bff.APIs.series_relation.helpers.scenes import (
                SeriesRelationScenes,
            )

            self._Scenes = SeriesRelationScenes
        return self

    def fetch_page(
        self, page: int, limit: int
    ) -> Tuple[List[Dict[str, Any]], int]:
        assert self._Scenes is not None
        return self._Scenes.fetch_page(page, limit)

    def get_scene(self, key: str) -> Dict[str, Any]:
        assert self._Scenes is not None
        return self._Scenes.get_scene(key)

    def save_scene(self, key: str, settings: Dict[str, Any]) -> Dict[str, Any]:
        assert self._Scenes is not None
        return self._Scenes.save_scene(key, settings)


catalog_impl = SeriesRelationCatalogImplementer()
