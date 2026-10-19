"""投资建议陷阱：固定口径回复，不编造策略 A/B/C。"""

from __future__ import annotations

from core.modules.agent.core.navigator.patterns import (
    is_investment_advice_trap,
    is_out_of_scope_web_question,
)
from core.modules.agent.core.navigator.router import route
from core.modules.agent.core.roles.guide.patterns import is_architecture_question
from core.modules.agent.core.navigator.advice_reply import format_strategy_summaries_reply


def test_advice_trap_detects_make_money_question():
    assert is_investment_advice_trap("告诉我什么策略赚钱？")
    assert is_investment_advice_trap("有没有能赚钱的策略")
    assert not is_investment_advice_trap("帮我看看 ma20_touch 的资金报告")


def test_format_strategy_summaries_uses_real_keys():
    text = format_strategy_summaries_reply(
        {
            "ok": True,
            "strategies": [
                {
                    "key": "ma20_touch",
                    "display_name": "ma20_touch",
                    "has_report": True,
                    "version_id": "3",
                    "summary": {
                        "total_return": -0.094,
                        "max_drawdown": 0.21,
                        "win_rate": 0.4,
                        "sharpe_ratio": -0.5,
                    },
                },
                {
                    "key": "empty_demo",
                    "display_name": "empty_demo",
                    "has_report": False,
                },
            ],
        }
    )
    assert "ma20_touch" in text
    assert "empty_demo" in text
    assert "策略 A" not in text
    assert "不能提供投资建议" in text
    assert "-9.40%" in text


def test_format_strategy_summaries_empty():
    text = format_strategy_summaries_reply({"ok": True, "strategies": []})
    assert "还没有可列出的策略" in text
    assert "投资建议" in text


def test_out_of_scope_web_detects_news_and_macro():
    assert is_out_of_scope_web_question("最近发生的法国暴乱会不会影响A股？")
    assert is_out_of_scope_web_question("告诉我最近AI和芯片的投资潜力还大不大？")
    assert is_out_of_scope_web_question("美联储最近一次利率决议结果是什么？")
    assert not is_out_of_scope_web_question("帮我看看 ma20_touch 的资金报告")
    assert not is_out_of_scope_web_question("帮我改一下止损并重跑回测")


def test_navigator_splits_guide_arch_and_worker():
    assert route(
        "NTQ 的回测四步架构原理是什么？", provider_id="ntq", mode="regex"
    ).kind == "guide_arch"
    assert route("帮我改止损并重跑回测", provider_id="ntq", mode="regex").kind == "worker"
    assert route("资金报告里的夏普怎么读？", provider_id="ntq", mode="regex").kind == "guide"
    assert is_architecture_question("userspace 隔离是什么设计？")


def test_navigator_cross_intent_pipeline():
    advice = route("推荐能赚钱的策略并帮我写一个", provider_id="ntq", mode="regex")
    assert advice.kind == "advice"
    assert advice.queue == ("advice", "worker")
    ident = route("NTQ 是什么，顺便帮我回测一下", provider_id="ntq", mode="regex")
    assert ident.kind == "identity"
    assert ident.queue == ("identity", "worker")
    oos = route(
        "法国暴乱影响 A 股吗，帮我改止损并重跑回测", provider_id="ntq", mode="regex"
    )
    assert oos.kind == "out_of_scope"
    assert oos.queue == ("out_of_scope", "worker")
