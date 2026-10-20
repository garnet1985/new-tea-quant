"""Guide system prompt loaders (text lives under ``prompts/guide/``)."""

from __future__ import annotations

from typing import FrozenSet

from core.modules.agent.core.prompt_store import load_prompt
from core.modules.agent.core.roles.prompt_common import param_text, product_identity_text
from core.modules.agent.core.tool_catalog import ToolCatalog

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
    return load_prompt("guide/arch.md").rstrip()


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
        "guide/wiki.md",
        variables={
            "identity": product_identity_text(),
            "tools": tools,
        },
    ).rstrip()
    excerpt = str(docs_excerpt or "").strip()
    if excerpt:
        body += "\n\n说明书摘录：\n" + excerpt
    return body
