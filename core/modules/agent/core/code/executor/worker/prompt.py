"""Worker system prompt loader（文案在 ``content/specific/worker/``）。"""

from __future__ import annotations

from core.modules.agent.core.code.executor.shared.prompt_common import (
    param_text,
    product_identity_text,
)
from core.modules.agent.core.code.executor.shared.prompt_loader import load_prompt
from core.modules.agent.core.code.tools.tool_catalog import ToolCatalog


def worker_system_prompt(catalog: ToolCatalog) -> str:
    tools_lines = []
    for spec in catalog.list_tools():
        if not spec.implemented:
            continue
        tools_lines.append(
            f"- {spec.name}：{spec.description} 参数：{param_text(spec.parameters)}"
        )
    tools = "\n".join(tools_lines) if tools_lines else "（无已实现工具）"
    return load_prompt(
        "specific/worker/system.md",
        variables={
            "identity": product_identity_text(),
            "tools": tools,
        },
    ).rstrip()
