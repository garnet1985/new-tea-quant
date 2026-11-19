"""模型决策解析：勿把混排的 tool JSON 当作用户可见回复。"""

from __future__ import annotations

from core.modules.agent.core.code.navigator.patterns import FORCE_WORK_RE
from core.modules.agent.core.code.executor.shared.decision import decision, usable_reply
from core.modules.agent.core.code.executor.worker.pipeline import (
    asks_user_permission,
    is_deferred_plan_reply,
    is_next_step_offer,
    is_portfolio_plan_confirm,
    is_test_plan_confirm,
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
    gap = (
        "帮我验证一下是不是出来跳空之后都会总有一天补回来？"
        "假如跳空是个机会我能不能利用跳空进行盈利？"
    )
    assert FORCE_WORK_RE.search(gap)
    assert FORCE_WORK_RE.search("帮我验证金叉之后是不是更容易上涨")
    assert not FORCE_WORK_RE.search("跳空在 K 线上是什么意思")
    assert not FORCE_WORK_RE.search("有没有能赚钱的策略")


def test_asks_user_permission():
    assert asks_user_permission("要我改 attribution.py 里的 stop_loss 配置后重跑吗？")
    assert not asks_user_permission("已改 stop_loss 为可扫列表并完成归因，结论如下。")
    assert not asks_user_permission(
        "要不要试试不同的止损和止盈会有什么不同结果？（归因）"
    )


def test_deferred_plan_reply():
    assert is_deferred_plan_reply(
        "根因没变。我接下来会：1. 改 attribution.py 2. 重跑归因 3. 读报告"
    )
    assert not is_deferred_plan_reply(
        "归因已完成。敏感度最高的是 stop_loss=-0.08，总收益如下。"
    )
    plan = (
        "## 测试计划\n"
        "- **量化策略**：均线金叉\n"
        "- **策略名称**：ma10_cross_ma30\n"
        "您觉得这个测试计划可行吗？如果需要改动，请告诉我；确认执行请直接说「执行」。"
    )
    assert not is_deferred_plan_reply(plan)


def test_is_test_plan_confirm():
    plan = (
        "## 测试计划\n"
        "- **量化策略**：10 日均线上穿 30 日均线当日视为机会\n"
        "- **策略名称**：ma10_cross_ma30\n"
        "- **出场目标**：止损 -10%；止盈按模板多段；最长持有 30 开盘日\n"
        "您觉得这个测试计划可行吗？如果需要改动，请告诉我；确认执行请直接说「执行」。"
    )
    assert is_test_plan_confirm(plan)
    assert not is_test_plan_confirm("回测已完成，结论如下。")
    assert not asks_user_permission(plan)


def test_is_next_step_offer():
    seen = [{"tool": "read_execution_report", "ok": True, "layer": "price"}]
    offer = (
        "## 建议\n"
        "下一步：要不要用 100 万元本金做一版资金模拟，看看最多 10 只持仓时的组合表现？"
        "（确认后我会先给出资金模拟计划）\n"
        "要不要试试不同的止损和止盈（归因）？"
    )
    assert is_next_step_offer(offer, seen)
    assert not is_next_step_offer(offer, [])
    assert not is_next_step_offer("结论如下，机会总数 12。", seen)


def test_is_portfolio_plan_confirm():
    plan = (
        "## 资金模拟计划\n"
        "- **模拟本金**：100 万元\n"
        "- **最多同时持有**：10 只\n"
        "- **资金怎么分**：等额资金\n"
        "您觉得这个资金模拟计划可行吗？如果需要改动，请告诉我；确认执行请直接说「执行」。"
    )
    assert is_portfolio_plan_confirm(plan)
    assert not asks_user_permission(plan)
    assert not is_deferred_plan_reply(plan)
    assert not is_next_step_offer(plan, [{"tool": "read_execution_report", "ok": True}])
