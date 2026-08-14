"""Data contract BFF implementer."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple


class DataContractImplementer:
    def __init__(self) -> None:
        self._fetch_page = None

    def lazy_load(self) -> "DataContractImplementer":
        if self._fetch_page is None:
            from core.bff.APIs.data.contracts.helpers.contract_catalog import (
                fetch_data_contract_catalog_page,
            )

            self._fetch_page = fetch_data_contract_catalog_page
        return self

    def fetch_catalog_page(
        self, page: int, limit: int
    ) -> Tuple[List[Dict[str, Any]], int]:
        assert self._fetch_page is not None
        return self._fetch_page(page, limit)


impl = DataContractImplementer()
