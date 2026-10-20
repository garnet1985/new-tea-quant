"""介绍者 wiki 路径注入 docs_wiki.allowlist。"""

from __future__ import annotations

from core.modules.agent.core.code.executor.guider.docs import load_allowlisted_docs
from core.modules.agent.core.code.executor.guider.prompt import wiki_system_prompt
from core.modules.agent.core.code.tools.tool_catalog import ToolCatalog


def test_wiki_allowlist_loads_overview():
    docs = load_allowlisted_docs("docs_wiki.allowlist")
    assert "ntq_overview" in docs or "New Tea Quant" in docs or "NTQ" in docs


def test_wiki_system_prompt_embeds_docs_excerpt():
    catalog = ToolCatalog()
    prompt = wiki_system_prompt(catalog, docs_excerpt="### fixture\nhello-wiki-doc")
    assert "说明书摘录" in prompt
    assert "hello-wiki-doc" in prompt
    assert "list_strategy_summaries" in prompt
