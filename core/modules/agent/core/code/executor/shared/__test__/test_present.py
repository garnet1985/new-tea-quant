"""present 阶段：scenario 解析与透传 / 套模版。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.modules.agent.core.code.executor.shared.present import (
    resolve_present_scenario,
    run_present,
)


def test_resolve_backtest_price_needs_tool_and_intent() -> None:
    tools = [{"tool": "read_execution_report", "ok": True, "layer": "price"}]
    assert resolve_present_scenario("帮我总结一下价格层", tools) == "backtest_price"
    assert resolve_present_scenario("帮我总结一下价格层", []) is None
    assert (
        resolve_present_scenario(
            "随便聊聊",
            [{"tool": "read_execution_report", "ok": True, "layer": "price"}],
        )
        is None
    )
    assert (
        resolve_present_scenario(
            "帮我总结",
            [{"tool": "read_execution_report", "ok": True, "layer": "portfolio"}],
        )
        is None
    )


def test_run_present_passthrough_without_scenario() -> None:
    assert run_present(
        conclusion="原样结论",
        scenario=None,
        provider_id="deepseek",
    ) == "原样结论"


def test_run_present_calls_ask_with_template(monkeypatch) -> None:
    calls: List[Dict[str, Any]] = []

    def fake_ask(
        messages: List[Dict[str, str]],
        *,
        provider_id: str,
        max_tokens: int = 0,
        timeout_seconds: Optional[float] = None,
        extra_body: Any = None,
        ntq_phase: str = "",
        ntq_intent: Optional[str] = None,
        billing: Any = None,
    ) -> str:
        calls.append(
            {
                "messages": messages,
                "provider_id": provider_id,
                "ntq_phase": ntq_phase,
                "ntq_intent": ntq_intent,
            }
        )
        return "格式化后的报告"

    monkeypatch.setattr(
        "core.modules.agent.core.code.executor.shared.present.ask",
        fake_ask,
    )
    out = run_present(
        conclusion="胜率 0.55，共 10 笔",
        scenario="backtest_price",
        provider_id="ntq",
    )
    assert out == "格式化后的报告"
    assert len(calls) == 1
    assert calls[0]["ntq_phase"] == "act"
    assert calls[0]["ntq_intent"] == "present"
    blob = "\n".join(m["content"] for m in calls[0]["messages"])
    assert "backtest_price" in blob
    assert "胜率 0.55" in blob
    assert "收益成绩单" in blob


def test_run_present_fallback_on_ask_error(monkeypatch) -> None:
    def boom(*_a: Any, **_k: Any) -> str:
        raise RuntimeError("network")

    monkeypatch.setattr(
        "core.modules.agent.core.code.executor.shared.present.ask",
        boom,
    )
    assert (
        run_present(
            conclusion="兜底结论",
            scenario="backtest_price",
            provider_id="ntq",
        )
        == "兜底结论"
    )
