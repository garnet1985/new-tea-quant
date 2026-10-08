"""Data contract BFF implementer."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple


class DataContractImplementer:
    def __init__(self) -> None:
        self._fetch_page = None
        self._reload = None

    def lazy_load(self) -> "DataContractImplementer":
        if self._fetch_page is None:
            from core.bff.APIs.data.contracts.helpers.contract_catalog import (
                fetch_data_contract_catalog_page,
                reload_data_contract_catalog,
            )

            self._fetch_page = fetch_data_contract_catalog_page
            self._reload = reload_data_contract_catalog
        return self

    def fetch_catalog_page(
        self, page: int, limit: int, *, force_reload: bool = False
    ) -> Tuple[List[Dict[str, Any]], int]:
        assert self._fetch_page is not None
        return self._fetch_page(page, limit, force_reload=force_reload)

    def reload_catalog(self) -> Dict[str, Any]:
        assert self._reload is not None
        return self._reload()


impl = DataContractImplementer()
