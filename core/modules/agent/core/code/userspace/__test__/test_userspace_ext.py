"""Userspace agent 扩展：template / prompt / tool（经 ProjectContext + Discovery）。"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.modules.agent.core.code.conf.conf import USERSPACE_PROMPT_SNIPPET_MAX_CHARS
from core.modules.agent.core.code.executor.shared.present import (
    load_template,
    resolve_present_scenario,
)
from core.modules.agent.core.code.executor.worker.prompt import worker_system_prompt
from core.modules.agent.core.code.tools.tool_catalog import ToolCatalog
from core.modules.agent.core.code.tools.tool_runner import run_tool
from core.modules.agent.core.code.userspace import prompts as us_prompts
from core.modules.agent.core.code.userspace import templates as us_templates
from core.modules.agent.core.code.userspace import tools as us_tools


@pytest.fixture()
def agent_ext(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "agent"
    (root / "templates").mkdir(parents=True)
    (root / "prompts").mkdir(parents=True)
    (root / "tools").mkdir(parents=True)

    monkeypatch.setattr(
        "core.infra.project_context.ProjectContext.path.get_agent_extensions_directory",
        lambda: root,
    )
    monkeypatch.setattr(
        "core.infra.project_context.ProjectContext.path.get_agent_templates_directory",
        lambda: root / "templates",
    )
    monkeypatch.setattr(
        "core.infra.project_context.ProjectContext.path.get_agent_prompts_directory",
        lambda: root / "prompts",
    )
    monkeypatch.setattr(
        "core.infra.project_context.ProjectContext.path.get_agent_tools_directory",
        lambda: root / "tools",
    )
    return root


def test_template_override_builtin(agent_ext: Path) -> None:
    (agent_ext / "templates" / "backtest_price.md").write_text(
        "# 用户自定义价格层版式\n\n只有这一句。\n",
        encoding="utf-8",
    )
    text = load_template("backtest_price")
    assert "用户自定义价格层版式" in text
    assert "收益成绩单" not in text


def test_new_template_match(agent_ext: Path) -> None:
    (agent_ext / "templates" / "my_portfolio.md").write_text(
        "---\n"
        "match:\n"
        "  tool: read_execution_report\n"
        "  layer: portfolio\n"
        "  user_re: 总结|解读\n"
        "---\n\n"
        "# 资金层自定义\n",
        encoding="utf-8",
    )
    tools = [{"tool": "read_execution_report", "ok": True, "layer": "portfolio"}]
    assert resolve_present_scenario("帮我总结资金层", tools) == "my_portfolio"
    assert resolve_present_scenario("帮我总结资金层", []) is None


def test_prompt_append_and_truncate(agent_ext: Path) -> None:
    (agent_ext / "prompts" / "worker.md").write_text(
        "请用更短的条目写结论。\n",
        encoding="utf-8",
    )
    catalog = ToolCatalog()
    prompt = worker_system_prompt(catalog)
    assert "用户扩展" in prompt
    assert "更短的条目" in prompt
    assert "与上方冲突时以上方" in prompt

    long = "x" * (USERSPACE_PROMPT_SNIPPET_MAX_CHARS + 50)
    (agent_ext / "prompts" / "worker.md").write_text(long, encoding="utf-8")
    snip = us_prompts.load_userspace_prompt_snippet("worker")
    assert len(snip) <= USERSPACE_PROMPT_SNIPPET_MAX_CHARS + 5
    assert snip.endswith("…")


def test_tool_new_only_and_run(agent_ext: Path) -> None:
    tool_dir = agent_ext / "tools" / "ping_tool"
    tool_dir.mkdir()
    (tool_dir / "tool.py").write_text(
        "TOOL = {\n"
        '  "name": "ping_tool",\n'
        '  "description": "ping",\n'
        '  "parameters": {"type": "object", "properties": {}, '
        '"required": [], "additionalProperties": False},\n'
        "}\n"
        "def run(arguments):\n"
        '  return {"ok": True, "pong": True}\n',
        encoding="utf-8",
    )
    conflict = agent_ext / "tools" / "create_strategy"
    conflict.mkdir()
    (conflict / "tool.py").write_text(
        "TOOL = {\n"
        '  "name": "create_strategy",\n'
        '  "description": "should be ignored",\n'
        '  "parameters": {"type": "object", "properties": {}, '
        '"required": [], "additionalProperties": False},\n'
        "}\n"
        "def run(arguments):\n"
        '  return {"ok": True}\n',
        encoding="utf-8",
    )
    catalog = ToolCatalog()
    names = {spec.name for spec in catalog.list_tools()}
    assert "ping_tool" in names
    assert catalog.get("create_strategy") is not None
    specs = us_tools.list_userspace_tool_specs(builtin_names=catalog.builtin_names())
    assert all(s.name != "create_strategy" for s in specs)
    result = run_tool(catalog, "ping_tool", {})
    assert result.get("ok") is True
    assert result.get("pong") is True


def test_override_ignores_user_match_frontmatter(agent_ext: Path) -> None:
    (agent_ext / "templates" / "backtest_price.md").write_text(
        "---\n"
        "match:\n"
        "  tool: read_scan_report\n"
        "  user_re: 扫描\n"
        "---\n\n"
        "# override body\n",
        encoding="utf-8",
    )
    tools = [{"tool": "read_scan_report", "ok": True}]
    assert resolve_present_scenario("扫描总结", tools) is None
    price_tools = [{"tool": "read_execution_report", "ok": True, "layer": "price"}]
    assert resolve_present_scenario("帮我总结价格层", price_tools) == "backtest_price"
    assert "override body" in us_templates.load_merged_template("backtest_price")
