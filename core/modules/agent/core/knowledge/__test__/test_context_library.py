"""agent knowledge context_library 基础扫描。"""

from __future__ import annotations

from core.modules.agent.core.knowledge.context_library import list_context_docs


def test_list_context_docs_finds_overview():
    docs = list_context_docs()
    ids = {item.doc_id for item in docs}
    assert any("ntq_overview" in doc_id for doc_id in ids)
