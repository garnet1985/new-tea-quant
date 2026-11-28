"""complete_result：ntq 与自备 provider 路由。"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import pytest

from core.infra.ai.contracts import AiError, CompleteResult
from core.modules.agent.contracts import AgentError
from core.modules.agent.core.code.conf.conf import PRODUCT_PROVIDER_ID
from core.modules.agent.core.code.executor.shared import complete as complete_mod


def test_complete_result_ntq_uses_member_channel(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, Any] = {}

    def fake_complete(
        messages: Sequence[Mapping[str, str]],
        *,
        max_tokens: int = 2048,
        temperature: float = 0.2,
        timeout_seconds=None,
        extra_body=None,
    ) -> CompleteResult:
        seen["messages"] = list(messages)
        seen["extra_body"] = extra_body
        return CompleteResult(
            reply="ok",
            provider_id=PRODUCT_PROVIDER_ID,
            model="glm-4-flash",
            ntq={"catfood_spent": 0.1},
        )

    import core.modules.ntq_external.ai.member_channel as mc

    monkeypatch.setattr(mc, "complete", fake_complete)

    out = complete_mod.complete_result(
        [{"role": "user", "content": "hi"}],
        provider_id=PRODUCT_PROVIDER_ID,
        extra_body={"ntq": {"phase": "navigate"}},
    )
    assert out.reply == "ok"
    assert seen["extra_body"] == {"ntq": {"phase": "navigate"}}


def test_complete_result_own_uses_ai_channel(monkeypatch: pytest.MonkeyPatch) -> None:
    from core.infra.ai import AiChannel

    def fake_complete(*_a, **kwargs) -> CompleteResult:
        return CompleteResult(
            reply="local",
            provider_id=str(kwargs.get("provider_id") or "deepseek"),
            model="deepseek-chat",
        )

    monkeypatch.setattr(AiChannel, "complete", staticmethod(fake_complete))
    out = complete_mod.complete_result(
        [{"role": "user", "content": "hi"}],
        provider_id="deepseek",
    )
    assert out.reply == "local"
    assert out.provider_id == "deepseek"


def test_complete_result_maps_ai_error(monkeypatch: pytest.MonkeyPatch) -> None:
    from core.infra.ai import AiChannel

    def boom(*_a, **_k):
        raise AiError("no key")

    monkeypatch.setattr(AiChannel, "complete", staticmethod(boom))
    with pytest.raises(AgentError, match="no key"):
        complete_mod.complete_result(
            [{"role": "user", "content": "x"}],
            provider_id="deepseek",
        )