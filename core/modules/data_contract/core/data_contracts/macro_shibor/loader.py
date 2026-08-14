"""MacroShibor Loader。"""
from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

from core.modules.data_contract.core.base.base_loader import BaseDataContractLoader
from core.modules.data_manager import DataManager


class MacroShiborLoader(BaseDataContractLoader):
    """加载全局 sys_shibor（日度序列）。"""

    def load(
        self,
        params: Mapping[str, Any],
        context: Optional[Mapping[str, Any]] = None,
    ) -> Any:
        dm = DataManager()
        return dm.macro.load_shibor()

    def load_batch(
        self,
        entity_ids: Sequence[str],
        params: Mapping[str, Any],
        context: Optional[Mapping[str, Any]] = None,
    ) -> Mapping[str, Any]:
        data = self.load(params, context)
        return {str(eid).strip(): data for eid in entity_ids if str(eid).strip()}
