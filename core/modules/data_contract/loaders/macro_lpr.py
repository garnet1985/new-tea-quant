from __future__ import annotations

from typing import Any, Mapping, Optional

from core.modules.data_contract.loaders.base import BaseLoader
from core.modules.data_manager import DataManager


class MacroLprLoader(BaseLoader):
    """加载全局 sys_lpr（日度序列）。"""

    def load(self, params: Mapping[str, Any], context: Optional[Mapping[str, Any]] = None) -> Any:
        dm = DataManager()
        return dm.macro.load_lpr()
