"""投资建议陷阱：固定口径回复，不编造策略 A/B/C。"""

from __future__ import annotations

from core.modules.agent.core.run_loop import (
    _format_strategy_summaries_reply,
    _is_investment_advice_trap,
)


def test_advice_trap_detects_make_money_question():
    assert _is_investment_advice_trap("告诉我什么策略赚钱？")
    assert _is_investment_advice_trap("有没有能赚钱的策略")
    assert not _is_investment_advice_trap("帮我看看 ma20_touch 的资金报告")


def test_format_strategy_summaries_uses_real_keys():
    text = _format_strategy_summaries_reply(
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
    text = _format_strategy_summaries_reply({"ok": True, "strategies": []})
    assert "还没有可列出的策略" in text
    assert "投资建议" in text
