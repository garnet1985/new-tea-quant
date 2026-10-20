"""Guide system prompt loaders（文案在 ``content/specific/guider/``）。"""

from __future__ import annotations

from typing import FrozenSet

from core.modules.agent.core.code.executor.shared.prompt_common import (
    param_text,
    product_identity_text,
)
from core.modules.agent.core.code.executor.shared.prompt_loader import load_prompt
from core.modules.agent.core.code.tools.tool_catalog import ToolCatalog
from core.modules.agent.core.code.userspace.prompts import append_userspace_prompt

WIKI_READ_TOOLS: FrozenSet[str] = frozenset(
    {
        "read_progress",
        "list_strategy_summaries",
        "read_execution_report",
        "read_attribution_report",
        "read_scan_report",
    }
)


def arch_system_prompt() -> str:
    return load_prompt("specific/guider/arch.md").rstrip()


def wiki_system_prompt(catalog: ToolCatalog, *, docs_excerpt: str = "") -> str:
    tools_lines = []
    for spec in catalog.list_tools():
        if spec.name not in WIKI_READ_TOOLS or not spec.implemented:
            continue
        tools_lines.append(
            f"- {spec.name}：{spec.description} 参数：{param_text(spec.parameters)}"
        )
    tools = "\n".join(tools_lines) if tools_lines else "（无只读工具）"
    body = load_prompt(
        "specific/guider/wiki.md",
        variables={
            "identity": product_identity_text(),
            "tools": tools,
        },
    ).rstrip()
    style = load_prompt("specific/guider/answer_style.md").rstrip()
    if style:
        body += "\n\n" + style
    excerpt = str(docs_excerpt or "").strip()
    if excerpt:
        body += "\n\n说明书摘录：\n" + excerpt
    return append_userspace_prompt(body, "guider")
