"""按清单执行已实现的工具。"""

from __future__ import annotations

from typing import Any, Callable, Dict

from core.modules.agent.contracts import AgentError
from core.modules.agent.core.code.tools.tool_catalog import ToolCatalog
from core.modules.agent.core.code.tools.strategy.background_run import (
    start_attribute_enumerate,
    start_attribute_portfolio,
    start_attribute_price,
    start_enumerate,
    start_portfolio,
    start_price_factor,
    start_rolling,
    start_scan,
    start_simulate,
)
from core.modules.agent.core.code.tools.strategy.create_strategy import create_strategy
from core.modules.agent.core.code.tools.strategy.read_reports import (
    list_strategy_summaries,
    read_attribution_report,
    read_execution_report,
    read_progress,
    read_scan_report,
)
from core.modules.agent.core.code.tools.strategy.validate_strategy import validate_strategy
from core.modules.agent.core.code.tools.strategy.write_strategy_files import (
    write_strategy_files,
)

_HANDLERS: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
    "create_strategy": create_strategy,
    "write_strategy_files": write_strategy_files,
    "validate_strategy": validate_strategy,
    "start_enumerate": start_enumerate,
    "start_price_factor": start_price_factor,
    "start_portfolio": start_portfolio,
    "start_simulate": start_simulate,
    "start_attribute_enumerate": start_attribute_enumerate,
    "start_attribute_price": start_attribute_price,
    "start_attribute_portfolio": start_attribute_portfolio,
    "start_rolling": start_rolling,
    "start_scan": start_scan,
    "read_progress": read_progress,
    "list_strategy_summaries": list_strategy_summaries,
    "read_execution_report": read_execution_report,
    "read_attribution_report": read_attribution_report,
    "read_scan_report": read_scan_report,
}


def run_tool(
    catalog: ToolCatalog, name: str, arguments: Dict[str, Any] | None
) -> Dict[str, Any]:
    """执行一张调用单。未知或未实现的工具抛 AgentError。"""
    spec = catalog.get(name)
    if spec is None:
        raise AgentError(f"未知工具：{name}")
    if not spec.implemented:
        raise AgentError(f"工具尚未实现：{spec.name}")
    handler = _HANDLERS.get(spec.name)
    if handler is None:
        raise AgentError(f"工具尚未实现：{spec.name}")
    if arguments is None:
        arguments = {}
    if not isinstance(arguments, dict):
        raise AgentError("工具参数必须是对象")
    return handler(arguments)
