"""Tag catalog implementer (T1-01)."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple


class TagCatalogImplementer:
    def __init__(self) -> None:
        self._TagCatalog = None

    def lazy_load(self) -> "TagCatalogImplementer":
        if self._TagCatalog is None:
            from core.bff.APIs.tag.helpers.tag_catalog import TagCatalog

            self._TagCatalog = TagCatalog
        return self

    def fetch_page(
        self, page: int, limit: int
    ) -> Tuple[List[Dict[str, Any]], int, Dict[str, Any]]:
        assert self._TagCatalog is not None
        return self._TagCatalog.fetch_page(page, limit)


impl = TagCatalogImplementer()
