"""编排层：交出工具清单，并执行已实现的工具。"""

from __future__ import annotations

from typing import Any, Dict, List

from core.modules.agent.contracts import ToolSpec
from core.modules.agent.core.run_loop import RunLoop
from core.modules.agent.core.tool_catalog import ToolCatalog
from core.modules.agent.core.tool_runner import run_tool


class AgentManager:
    """内部编排。不对外导出。"""

    def __init__(self) -> None:
        self._catalog = ToolCatalog()

    def list_tools(self) -> List[ToolSpec]:
        return self._catalog.list_tools()

    def call_tool(
        self, name: str, arguments: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        return run_tool(self._catalog, name, arguments)

    def run(self, content: str) -> str:
        return RunLoop(self._catalog).run(content)
