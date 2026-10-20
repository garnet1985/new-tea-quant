"""prompt_store loads md-only prompts and sections."""

from __future__ import annotations

from core.modules.agent.core.prompt_store import load_nudge, load_prompt, load_reply
from core.modules.agent.core.roles.guide.prompt import arch_system_prompt, wiki_system_prompt
from core.modules.agent.core.roles.worker.prompt import worker_system_prompt
from core.modules.agent.core.tool_catalog import ToolCatalog


def test_load_identity_and_replies() -> None:
    identity = load_prompt("common/identity.md")
    assert "New Tea Quant" in identity
    assert "茶叶" in identity  # prohibition line
    intro = load_reply("product_intro")
    assert "New Tea Quant" in intro
    assert load_reply("out_of_scope_web")
    assert "不能提供投资建议" in load_reply("advice_head")
    assert "（超时）" in load_reply(
        "advice_list_unavailable", variables={"detail": "（超时）"}
    )
    assert load_prompt("common/session_preamble.md")


def test_worker_and_guide_prompts_assemble() -> None:
    catalog = ToolCatalog()
    worker = worker_system_prompt(catalog)
    assert "执行代理" in worker
    assert "create_strategy" in worker
    assert "New Tea Quant" in worker
    wiki = wiki_system_prompt(catalog, docs_excerpt="摘录测试")
    assert "产品向导" in wiki
    assert "摘录测试" in wiki
    assert "New Tea Quant" in arch_system_prompt()


def test_nudges() -> None:
    assert "机会数为 0" in load_nudge("worker", "zero_opportunity")
    assert "策略 A/B/C" in load_nudge("guide", "fabricated_strategy")
