from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

from core.modules.data_contract.loaders.base import BaseLoader
from core.modules.data_manager import DataManager


class MacroCpiLoader(BaseLoader):
    """加载全局 sys_cpi（月度序列）。"""

    def load(self, params: Mapping[str, Any], context: Optional[Mapping[str, Any]] = None) -> Any:
        dm = DataManager()
        return dm.macro.load_cpi()

    def load_batch(
        self,
        entity_ids: Sequence[str],
        params: Mapping[str, Any],
        context: Optional[Mapping[str, Any]] = None,
    ) -> Mapping[str, Any]:
        """
        批量加载宏观数据（GLOBAL scope：所有 entity 共享同一份数据）。
        """
        data = self.load(params, context)
        return {str(eid).strip(): data for eid in entity_ids if str(eid).strip()}
