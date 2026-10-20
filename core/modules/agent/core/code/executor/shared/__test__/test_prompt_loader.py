"""prompt_loader loads content/ md sections."""

from __future__ import annotations

from core.modules.agent.core.code.executor.guider.prompt import (
    arch_system_prompt,
    wiki_system_prompt,
)
from core.modules.agent.core.code.executor.shared.prompt_loader import (
    content_root,
    load_nudge,
    load_prompt,
    load_reply,
)
from core.modules.agent.core.code.executor.worker.prompt import worker_system_prompt
from core.modules.agent.core.code.tools.tool_catalog import ToolCatalog


def test_load_redlines_and_replies() -> None:
    redlines = load_prompt("global/redlines.md")
    assert "New Tea Quant" in redlines
    assert "茶叶" in redlines
    assert content_root().name == "content"
    intro = load_reply("intro")
    assert "New Tea Quant" in intro
    assert load_reply("out_of_scope")
    assert "不能提供投资建议" in load_reply("advice_head")
    assert "（超时）" in load_reply(
        "advice_list_unavailable", variables={"detail": "（超时）"}
    )
    assert load_prompt("global/session_preamble.md")
    assert load_reply("arch_unavailable")
    assert load_prompt("specific/navigator/classifier.md")


def test_worker_and_guide_prompts_assemble() -> None:
    from core.modules.agent.core.code.executor.shared.prompt_common import (
        product_identity_text,
    )

    identity = product_identity_text()
    assert "职责·能做" in identity
    assert "职责·不做" in identity
    catalog = ToolCatalog()
    worker = worker_system_prompt(catalog)
    assert "执行代理" in worker
    assert "create_strategy" in worker
    assert "New Tea Quant" in worker
    assert "职责·能做" in worker
    wiki = wiki_system_prompt(catalog, docs_excerpt="摘录测试")
    assert "产品向导" in wiki
    assert "摘录测试" in wiki
    assert "New Tea Quant" in arch_system_prompt()


def test_nudges() -> None:
    assert "机会数为 0" in load_nudge("worker", "zero_opportunity")
    assert "策略 A/B/C" in load_nudge("guide", "fabricated_strategy")
