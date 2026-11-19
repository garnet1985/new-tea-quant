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
from core.modules.agent.core.code.tools.tag.background_run import start_tag
from core.modules.agent.core.code.tools.tag.create_tag import create_tag
from core.modules.agent.core.code.tools.tag.read_reports import (
    list_tag_summaries,
    read_tag_report,
)
from core.modules.agent.core.code.tools.tag.validate_tag import validate_tag
from core.modules.agent.core.code.tools.tag.write_tag_files import write_tag_files
from core.modules.agent.core.code.tools.data.create_table import create_table
from core.modules.agent.core.code.tools.data.ensure_physical_table import (
    ensure_physical_table,
)
from core.modules.agent.core.code.tools.data.inspect_data import (
    check_data_freshness,
    describe_data_table,
    list_data_contract_keys,
    list_data_sources,
    list_data_tables,
)
from core.modules.agent.core.code.tools.data.validate_table import validate_table
from core.modules.agent.core.code.tools.data.write_table_files import write_table_files

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
    "create_tag": create_tag,
    "write_tag_files": write_tag_files,
    "validate_tag": validate_tag,
    "start_tag": start_tag,
    "list_tag_summaries": list_tag_summaries,
    "read_tag_report": read_tag_report,
    "list_data_tables": list_data_tables,
    "describe_data_table": describe_data_table,
    "list_data_contract_keys": list_data_contract_keys,
    "list_data_sources": list_data_sources,
    "check_data_freshness": check_data_freshness,
    "create_table": create_table,
    "write_table_files": write_table_files,
    "validate_table": validate_table,
    "ensure_physical_table": ensure_physical_table,
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
        from core.modules.agent.core.code.userspace.tools import get_userspace_tool_handler

        handler = get_userspace_tool_handler(
            spec.name,
            builtin_names=catalog.builtin_names(),
        )
    if handler is None:
        raise AgentError(f"工具尚未实现：{spec.name}")
    if arguments is None:
        arguments = {}
    if not isinstance(arguments, dict):
        raise AgentError("工具参数必须是对象")
    return handler(arguments)
