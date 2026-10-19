"""模型决策解析：勿把混排的 tool JSON 当作用户可见回复。"""

from __future__ import annotations

from core.modules.agent.core.gate.patterns import FORCE_WORK_RE
from core.modules.agent.core.loop_runtime import decision, usable_reply
from core.modules.agent.core.roles.worker.role import (
    asks_user_permission,
    is_deferred_plan_reply,
    is_zero_opportunity_report,
)


def test_decision_extracts_tool_from_prose_prefix():
    raw = (
        "抱歉刚才的回答有误。我将重新审查结果。\n"
        '{"tool":"read_progress","arguments":{}}\n'
        '{"tool":"read_progress","arguments":{}}'
    )
    chosen = decision(raw, {"read_progress"})
    assert chosen.get("tool") == "read_progress"
    assert chosen.get("arguments") == {}


def test_decision_prefers_tool_with_task_id():
    raw = (
        "复查中\n"
        '{"tool":"read_progress","arguments":{"task_id":"abc123"}}'
    )
    chosen = decision(raw, {"read_progress"})
    assert chosen == {
        "tool": "read_progress",
        "arguments": {"task_id": "abc123"},
    }


def test_usable_reply_strips_leaked_tool_json():
    raw = (
        "任务还在跑。\n"
        '{"tool":"read_progress","arguments":{"task_id":"t1"}}'
    )
    assert usable_reply(raw) == "任务还在跑。"


def test_usable_reply_rejects_tool_only_residue():
    assert usable_reply('{"tool":"read_progress","arguments":{}}') == ""


def test_decision_plain_reply_json():
    chosen = decision('{"reply":"机会数为 0，已核对字段名无误。"}', set())
    assert chosen.get("reply") == "机会数为 0，已核对字段名无误。"


def test_zero_opportunity_report_from_enum_summary():
    assert is_zero_opportunity_report(
        "read_execution_report",
        {
            "ok": True,
            "layer": "enum",
            "summary": {"total_opportunities": 0, "total_stocks": 300},
        },
    )
    assert not is_zero_opportunity_report(
        "read_execution_report",
        {
            "ok": True,
            "layer": "enum",
            "summary": {"total_opportunities": 12},
        },
    )


def test_zero_opportunity_report_portfolio_trades():
    assert is_zero_opportunity_report(
        "read_execution_report",
        {"ok": True, "layer": "portfolio", "summary": {"total_trades": 0}},
    )


def test_force_work_intents():
    assert FORCE_WORK_RE.search("帮我建一个20日均线的策略，告诉我结果")
    assert FORCE_WORK_RE.search("不可能，你是不是触发了缓存？")
    assert not FORCE_WORK_RE.search("NTQ 是什么")


def test_asks_user_permission():
    assert asks_user_permission("要我改 attribution.py 里的 stop_loss 配置后重跑吗？")
    assert not asks_user_permission("已改 stop_loss 为可扫列表并完成归因，结论如下。")


def test_deferred_plan_reply():
    assert is_deferred_plan_reply(
        "根因没变。我接下来会：1. 改 attribution.py 2. 重跑归因 3. 读报告"
    )
    assert not is_deferred_plan_reply(
        "归因已完成。敏感度最高的是 stop_loss=-0.08，总收益如下。"
    )
