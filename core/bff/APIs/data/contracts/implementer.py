"""Data contract BFF implementer."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from core.infra.project_context import ProjectContext
from core.modules.data_contract import ContractIssuer


class DataContractImplementer:
    def lazy_load(self) -> "DataContractImplementer":
        return self

    def fetch_catalog_page(
        self, page: int, limit: int, *, force_reload: bool = False
    ) -> Tuple[List[Dict[str, Any]], int]:
        return ContractIssuer.fetch_ui_catalog_page(
            page, limit, force_reload=force_reload
        )

    def reload_catalog(self) -> Dict[str, Any]:
        total = ContractIssuer.reload(
            user_space_path=ProjectContext.path.get_data_contract_root()
        )
        return {"total": int(total)}


impl = DataContractImplementer()
