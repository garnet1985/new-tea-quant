"""Tag catalog implementer (T1-01)."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from core.modules.tag import Tag


class TagCatalogImplementer:
    def lazy_load(self) -> "TagCatalogImplementer":
        return self

    def fetch_page(
        self, page: int, limit: int
    ) -> Tuple[List[Dict[str, Any]], int, Dict[str, Any]]:
        return Tag.fetch_catalog_page(page, limit)


impl = TagCatalogImplementer()
