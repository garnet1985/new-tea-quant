"""编排层：目前只交出工具清单。循环在 RunLoop，门面不导出。"""

from __future__ import annotations

from typing import List

from core.modules.agent.contracts import ToolSpec
from core.modules.agent.core.tool_catalog import ToolCatalog


class AgentManager:
    """内部编排。不对外导出。"""

    def __init__(self) -> None:
        self._catalog = ToolCatalog()

    def list_tools(self) -> List[ToolSpec]:
        return self._catalog.list_tools()
