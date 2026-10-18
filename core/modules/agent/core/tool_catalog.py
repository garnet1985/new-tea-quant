"""工具清单。本版只登记说明，不执行。"""

from __future__ import annotations

from typing import Any, Dict, List

from core.modules.agent.contracts import ToolSpec


def _object(properties: Dict[str, Any], required: List[str]) -> Dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


def _string(description: str) -> Dict[str, str]:
    return {"type": "string", "description": description}


_TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="create_strategy",
        description="从模板新建一个策略目录。目录已存在时拒绝，不覆盖。",
        parameters=_object(
            {"key": _string("策略目录名，与 meta.key 一致")},
            ["key"],
        ),
        implemented=False,
    ),
    ToolSpec(
        name="write_strategy_files",
        description="写入该策略的 strategy.py 与 settings.py。路径须通过写入准则。",
        parameters=_object(
            {
                "key": _string("策略目录名"),
                "strategy_py": _string("strategy.py 全文"),
                "settings_py": _string("settings.py 全文"),
            },
            ["key", "strategy_py", "settings_py"],
        ),
        implemented=False,
    ),
    ToolSpec(
        name="validate_strategy",
        description="检查钩子与 settings 能否被 NTQ 加载。未通过则不要启动回测。",
        parameters=_object({"key": _string("策略目录名")}, ["key"]),
        implemented=False,
    ),
    ToolSpec(
        name="start_simulate",
        description="启动组合回测并立即返回任务 id。不要等待回测结束。",
        parameters=_object(
            {
                "key": _string("策略目录名"),
                "years": _string("回测年数，例如 3"),
            },
            ["key", "years"],
        ),
        implemented=False,
    ),
    ToolSpec(
        name="read_progress",
        description="按任务 id 读取进度摘要。未结束时不要编造收益数字。",
        parameters=_object(
            {"task_id": _string("start_simulate 返回的任务 id")}, ["task_id"]
        ),
        implemented=False,
    ),
    ToolSpec(
        name="read_report",
        description="读取一版回测的摘要：总收益、最大回撤、夏普、交易次数、版本号、报告路径。",
        parameters=_object(
            {
                "key": _string("策略目录名"),
                "version_id": _string("版本号；空则读该任务对应的版本"),
            },
            ["key"],
        ),
        implemented=False,
    ),
)


class ToolCatalog:
    """已登记工具的只读清单。"""

    def list_tools(self) -> List[ToolSpec]:
        return list(_TOOLS)
