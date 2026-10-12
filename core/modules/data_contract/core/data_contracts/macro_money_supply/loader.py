"""货币供应量 Loader。"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from core.modules.data_contract.core.base.base_loader import BaseDataContractLoader
from core.modules.data_manager import DataManager


class MacroMoneySupplyLoader(BaseDataContractLoader):
    """加载全局 sys_money_supply（月度序列）。"""

    def load(self, params: Mapping[str, Any]) -> Any:
        return DataManager().macro.load_money_supply()

    def load_batch(
        self,
        entity_ids: Sequence[str],
        params: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        data = self.load(params)
        return {str(eid).strip(): data for eid in entity_ids if str(eid).strip()}
