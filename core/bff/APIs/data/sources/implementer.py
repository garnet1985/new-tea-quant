"""Data source BFF implementer."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


class DataSourceImplementer:
    def __init__(self) -> None:
        self._fetch_page = None
        self._fetch_freshness = None

    def lazy_load(self) -> "DataSourceImplementer":
        if self._fetch_page is None:
            from core.bff.APIs.data.sources.helpers.source_catalog import (
                fetch_data_source_catalog_page,
                fetch_data_source_freshness,
            )

            self._fetch_page = fetch_data_source_catalog_page
            self._fetch_freshness = fetch_data_source_freshness
        return self

    def fetch_catalog_page(
        self, page: int, limit: int
    ) -> Tuple[List[Dict[str, Any]], int, Dict[str, Any]]:
        assert self._fetch_page is not None
        return self._fetch_page(page, limit)

    def fetch_freshness(
        self, source_names: Optional[List[str]] = None
    ) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
        assert self._fetch_freshness is not None
        return self._fetch_freshness(source_names)


impl = DataSourceImplementer()
