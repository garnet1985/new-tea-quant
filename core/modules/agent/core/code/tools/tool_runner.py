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
    read_rolling_report,
    read_scan_report,
)
from core.modules.agent.core.code.tools.strategy.validate_strategy import validate_strategy
from core.modules.agent.core.code.tools.strategy.validate_strategy_rolling import (
    validate_strategy_rolling,
)
from core.modules.agent.core.code.tools.strategy.write_strategy_files import (
    write_strategy_files,
)
from core.modules.agent.core.code.tools.strategy.write_strategy_rolling import (
    write_strategy_rolling,
)
from core.modules.agent.core.code.tools.tag.background_run import start_tag
from core.modules.agent.core.code.tools.tag.create_tag import create_tag
from core.modules.agent.core.code.tools.tag.read_reports import (
    list_tag_summaries,
    read_tag_report,
)
from core.modules.agent.core.code.tools.tag.validate_tag import validate_tag
from core.modules.agent.core.code.tools.tag.write_tag_files import write_tag_files
from core.modules.agent.core.code.tools.data.create_data_contract import (
    create_data_contract,
)
from core.modules.agent.core.code.tools.data.create_data_source import create_data_source
from core.modules.agent.core.code.tools.data.create_table import create_table
from core.modules.agent.core.code.tools.data.describe_data_contract import (
    describe_data_contract,
)
from core.modules.agent.core.code.tools.data.ensure_physical_table import (
    ensure_physical_table,
)
from core.modules.agent.core.code.tools.data.inspect_data import (
    check_data_freshness,
    describe_data_table,
    list_data_contract_keys,
    list_data_sources,
    list_data_tables,
    list_indicators,
    list_stock_pool_dimensions,
)
from core.modules.agent.core.code.tools.data.renew import (
    read_renew_progress,
    start_data_renew,
)
from core.modules.agent.core.code.tools.data.register_data_contract_key import (
    register_data_contract_key,
)
from core.modules.agent.core.code.tools.data.register_data_source import (
    register_data_source,
)
from core.modules.agent.core.code.tools.data.validate_data_contract import (
    validate_data_contract,
)
from core.modules.agent.core.code.tools.data.validate_data_source import (
    validate_data_source,
)
from core.modules.agent.core.code.tools.data.validate_table import validate_table
from core.modules.agent.core.code.tools.data.write_data_contract_files import (
    write_data_contract_files,
)
from core.modules.agent.core.code.tools.data.write_data_source_files import (
    write_data_source_files,
)
from core.modules.agent.core.code.tools.data.write_table_files import write_table_files
from core.modules.agent.core.code.tools.series_relation.create_series_relation import (
    create_series_relation,
)
from core.modules.agent.core.code.tools.series_relation.inspect_series_relation import (
    describe_series_relation,
    list_series_relations,
)
from core.modules.agent.core.code.tools.series_relation.run_series_relation import (
    run_series_relation,
)
from core.modules.agent.core.code.tools.series_relation.validate_series_relation import (
    validate_series_relation,
)
from core.modules.agent.core.code.tools.series_relation.write_series_relation_settings import (
    write_series_relation_settings,
)
from core.modules.agent.core.code.tools.post_process.create_adapter import (
    create_post_process_adapter,
)
from core.modules.agent.core.code.tools.post_process.create_processor import (
    create_post_process_processor,
)
from core.modules.agent.core.code.tools.post_process.inspect_post_process import (
    describe_post_process_adapter,
    describe_post_process_processor,
    list_post_process_adapters,
    list_post_process_processors,
)
from core.modules.agent.core.code.tools.post_process.validate_adapter import (
    validate_post_process_adapter,
)
from core.modules.agent.core.code.tools.post_process.validate_processor import (
    validate_post_process_processor,
)
from core.modules.agent.core.code.tools.post_process.write_adapter_files import (
    write_post_process_adapter_files,
)
from core.modules.agent.core.code.tools.post_process.write_processor import (
    write_post_process_processor,
)
from core.modules.agent.core.code.tools.post_process.enable import (
    get_post_process_run_enabled,
    set_post_process_run_enabled,
    set_post_processor_enabled,
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
    "write_strategy_rolling": write_strategy_rolling,
    "validate_strategy_rolling": validate_strategy_rolling,
    "read_progress": read_progress,
    "list_strategy_summaries": list_strategy_summaries,
    "read_execution_report": read_execution_report,
    "read_attribution_report": read_attribution_report,
    "read_scan_report": read_scan_report,
    "read_rolling_report": read_rolling_report,
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
    "list_indicators": list_indicators,
    "list_stock_pool_dimensions": list_stock_pool_dimensions,
    "start_data_renew": start_data_renew,
    "read_renew_progress": read_renew_progress,
    "create_table": create_table,
    "write_table_files": write_table_files,
    "validate_table": validate_table,
    "ensure_physical_table": ensure_physical_table,
    "create_data_source": create_data_source,
    "write_data_source_files": write_data_source_files,
    "register_data_source": register_data_source,
    "validate_data_source": validate_data_source,
    "create_data_contract": create_data_contract,
    "write_data_contract_files": write_data_contract_files,
    "register_data_contract_key": register_data_contract_key,
    "validate_data_contract": validate_data_contract,
    "describe_data_contract": describe_data_contract,
    "create_series_relation": create_series_relation,
    "write_series_relation_settings": write_series_relation_settings,
    "validate_series_relation": validate_series_relation,
    "list_series_relations": list_series_relations,
    "describe_series_relation": describe_series_relation,
    "run_series_relation": run_series_relation,
    "create_post_process_adapter": create_post_process_adapter,
    "write_post_process_adapter_files": write_post_process_adapter_files,
    "validate_post_process_adapter": validate_post_process_adapter,
    "create_post_process_processor": create_post_process_processor,
    "write_post_process_processor": write_post_process_processor,
    "validate_post_process_processor": validate_post_process_processor,
    "list_post_process_adapters": list_post_process_adapters,
    "list_post_process_processors": list_post_process_processors,
    "describe_post_process_adapter": describe_post_process_adapter,
    "describe_post_process_processor": describe_post_process_processor,
    "set_post_processor_enabled": set_post_processor_enabled,
    "set_post_process_run_enabled": set_post_process_run_enabled,
    "get_post_process_run_enabled": get_post_process_run_enabled,
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
