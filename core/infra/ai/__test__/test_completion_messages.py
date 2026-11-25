"""_completion_messages trim when tool loops exceed the 40-cap."""

from __future__ import annotations

import pytest

from core.infra.ai.contracts import AiError
from core.infra.ai.core.ai_channel_manager import (
    _MAX_COMPLETION_MESSAGES,
    _completion_messages,
)

pytestmark = pytest.mark.force_run


def test_empty_still_rejected() -> None:
    with pytest.raises(AiError, match="消息条数"):
        _completion_messages([])


def test_trim_keeps_system_and_tail() -> None:
    messages = [{"role": "system", "content": "sys"}]
    for i in range(50):
        messages.append({"role": "user", "content": f"u{i}"})
        messages.append({"role": "assistant", "content": f"a{i}"})
    out = _completion_messages(messages)
    assert len(out) == _MAX_COMPLETION_MESSAGES
    assert out[0]["role"] == "system"
    assert out[0]["content"] == "sys"
    assert out[-1]["content"] == "a49"
    assert any(row["role"] == "user" for row in out)


def test_under_limit_unchanged() -> None:
    messages = [
        {"role": "system", "content": "s"},
        {"role": "user", "content": "hi"},
    ]
    assert _completion_messages(messages) == messages
