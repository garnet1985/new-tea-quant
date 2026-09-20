"""百科发现与挑选：嵌套目录、预算、中文关键词。"""

from __future__ import annotations

from core.modules.assistant.core.context_library import (
    ContextDoc,
    compose_knowledge,
    keyword_pick,
    list_context_docs,
    parse_picked_ids,
)


def _doc(doc_id: str, title: str, body: str, *, kind: str = "wiki", summary: str = "") -> ContextDoc:
    return ContextDoc(
        doc_id=doc_id,
        kind=kind,
        title=title,
        aliases=(),
        summary=summary,
        body=body,
    )


def test_discovers_nested_wiki_strategy() -> None:
    ids = {item.doc_id for item in list_context_docs()}
    assert "wiki/strategy/strategy_decision" in ids
    assert "wiki/strategy/backtest_pipeline" in ids
    assert "know_how/config_strategy_settings" in ids


def test_parse_picked_ids_accepts_nested_path() -> None:
    allowed = {"wiki/strategy/strategy_decision", "wiki/tag"}
    assert parse_picked_ids(
        '["wiki/strategy/strategy_decision"]',
        allowed,
    ) == ["wiki/strategy/strategy_decision"]


def test_keyword_pick_matches_chinese_question() -> None:
    docs = [
        _doc("wiki/tag", "标签", "tag body", summary="选股标签"),
        _doc(
            "wiki/strategy/strategy_decision",
            "NTQ 决策者模拟",
            "decision body",
            summary="回测第四步 决策者模拟",
        ),
    ]
    picked = keyword_pick("决策者模式是什么", docs)
    assert picked[0] == "wiki/strategy/strategy_decision"


def test_compose_knowledge_keeps_picked_when_global_is_huge() -> None:
    global_docs = [
        _doc("global/huge", "大参考", "G" * 40000, kind="global"),
        _doc("global/system_role", "系统角色", "你是 NTQ 助手。", kind="global"),
    ]
    selected = [
        _doc("wiki/strategy/strategy_decision", "决策者模式", "决策者按日选股买多少。"),
    ]
    text = compose_knowledge(global_docs, selected)
    assert "决策者按日选股买多少" in text
    assert "你是 NTQ 助手" in text
