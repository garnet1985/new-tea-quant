"""Data source BFF implementer."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from core.modules.data_source import DataSourceManager


class DataSourceImplementer:
    def lazy_load(self) -> "DataSourceImplementer":
        return self

    def fetch_catalog_page(
        self, page: int, limit: int
    ) -> Tuple[List[Dict[str, Any]], int, Dict[str, Any]]:
        return DataSourceManager.fetch_catalog_page(page, limit)

    def fetch_freshness(
        self, source_names: Optional[List[str]] = None
    ) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
        return DataSourceManager.fetch_freshness(source_names)


impl = DataSourceImplementer()
