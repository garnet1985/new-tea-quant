"""有通用凭证时对话走官网；指定供应商时仍走本机密钥。"""

from __future__ import annotations

from pathlib import Path

from core.modules.assistant.contracts import AssistantError, ProviderInfo
from core.modules.assistant.core import assistant_manager as manager_mod
from core.modules.assistant.core.assistant_manager import AssistantManager
from core.modules.assistant.core import member_channel
from core.modules.assistant.core.member_channel import DEFAULT_BASE_URL, member_base_url
from core.modules.assistant.core.openai_compatible_client import (
    _DEFAULT_TIMEOUT_SECONDS,
)


TOKEN = "ntq_" + "ab" * 24


class RecordingClient:
    def __init__(self, fail_with: str = ""):
        self.calls = []
        self.fail_with = fail_with

    def complete(self, **kwargs):
        self.calls.append(kwargs)
        if self.fail_with:
            raise AssistantError(self.fail_with)
        return "pong"


def _local_provider() -> ProviderInfo:
    return ProviderInfo(
        provider_id="zhipu",
        directory=Path("/tmp/zhipu"),
        base_url="https://open.bigmodel.cn/api/paas/v4",
        model="glm-4-flash",
        enabled=True,
        has_api_key=True,
    )


def _manager(monkeypatch, client: RecordingClient) -> AssistantManager:
    manager = AssistantManager(client)
    monkeypatch.setattr(manager, "_knowledge_for_question", lambda *args, **kwargs: "")
    monkeypatch.setattr(manager, "_resolve_provider", lambda provider_id: _local_provider())
    monkeypatch.setattr(manager._catalog, "load_api_key", lambda directory: "local-key")
    return manager


def test_membership_chat_uses_official_site(monkeypatch):
    monkeypatch.setattr(manager_mod, "member_token", lambda: TOKEN)
    monkeypatch.setattr(
        manager_mod,
        "member_base_url",
        lambda: "http://localhost:2026/api/v1/ntq-ai",
    )
    client = RecordingClient()
    result = _manager(monkeypatch, client).chat("你好")
    assert result.reply == "pong"
    assert result.provider_id == "ntq"
    assert result.model == "glm-4-flash"
    assert client.calls[0]["base_url"] == "http://localhost:2026/api/v1/ntq-ai"
    assert client.calls[0]["api_key"] == TOKEN
    assert _DEFAULT_TIMEOUT_SECONDS <= 25


def test_explicit_ntq_uses_member_channel(monkeypatch):
    monkeypatch.setattr(manager_mod, "member_token", lambda: TOKEN)
    monkeypatch.setattr(
        manager_mod,
        "member_base_url",
        lambda: "http://localhost:2026/api/v1/ntq-ai",
    )
    client = RecordingClient()
    result = _manager(monkeypatch, client).chat("你好", provider_id="ntq")
    assert result.provider_id == "ntq"
    assert client.calls[0]["api_key"] == TOKEN


def test_explicit_provider_keeps_local_key(monkeypatch):
    monkeypatch.setattr(manager_mod, "member_token", lambda: TOKEN)
    client = RecordingClient()
    result = _manager(monkeypatch, client).chat("你好", provider_id="zhipu")
    assert result.provider_id == "zhipu"
    assert client.calls[0]["api_key"] == "local-key"
    assert "bigmodel" in client.calls[0]["base_url"]


def test_member_connection_error_is_rewritten(monkeypatch):
    monkeypatch.setattr(manager_mod, "member_token", lambda: TOKEN)
    monkeypatch.setattr(manager_mod, "member_base_url", lambda: DEFAULT_BASE_URL)
    client = RecordingClient(fail_with="无法连接供应商：refused")
    try:
        _manager(monkeypatch, client).chat("你好")
    except AssistantError as exc:
        message = str(exc)
    else:
        raise AssertionError("expected AssistantError")
    assert "官网" in message
    assert TOKEN not in message
    assert "local-key" not in message


def test_base_url_env_then_userspace_then_default(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("NTQ_MEMBER_AI_BASE_URL", raising=False)
    monkeypatch.setattr(
        member_channel.ProjectContext.path,
        "get_user_config_root",
        lambda: tmp_path,
    )
    assert member_base_url() == DEFAULT_BASE_URL

    (tmp_path / "membership.json").write_text(
        '{"ai_base_url": "http://localhost:2026/api/v1/ntq-ai"}',
        encoding="utf-8",
    )
    assert member_base_url() == "http://localhost:2026/api/v1/ntq-ai"

    monkeypatch.setenv("NTQ_MEMBER_AI_BASE_URL", "https://www.new-tea.cn/api/v1/ntq-ai/")
    assert member_base_url() == "https://www.new-tea.cn/api/v1/ntq-ai"
