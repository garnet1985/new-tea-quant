"""API contract tests for modules.assistant Facade."""

from __future__ import annotations

import os
import unittest

import pytest

from core.infra.project_context import ProjectContext
from core.modules.assistant import Assistant
from core.modules.assistant.contracts import AssistantError, ProviderInfo

pytestmark = pytest.mark.force_run


class TestAssistantApi(unittest.TestCase):
    def test_facade_export(self) -> None:
        import core.modules.assistant as pkg

        self.assertEqual(pkg.__all__, ["Assistant"])
        self.assertFalse(hasattr(pkg, "ProviderInfo"))
        self.assertFalse(hasattr(pkg, "AssistantManager"))
        self.assertFalse(hasattr(pkg, "OpenAICompatibleClient"))
        self.assertFalse(hasattr(pkg, "list_providers"))
        self.assertFalse(hasattr(pkg, "chat"))

    def test_list_and_get_callable(self) -> None:
        self.assertTrue(callable(Assistant.list_providers))
        self.assertTrue(callable(Assistant.get_provider))
        self.assertTrue(callable(Assistant.set_api_key))
        self.assertTrue(callable(Assistant.chat))
        self.assertIsNone(Assistant.get_provider(""))
        self.assertIsNone(Assistant.get_provider("../secret"))
        providers = Assistant.list_providers()
        self.assertIsInstance(providers, list)

    def test_chat_rejects_blank_content(self) -> None:
        with self.assertRaises(AssistantError) as ctx:
            Assistant.chat("   ")
        self.assertIn("空", str(ctx.exception))
        self.assertNotIn("Bearer", str(ctx.exception))

    def test_provider_info_fields(self) -> None:
        fields = {item.name for item in ProviderInfo.__dataclass_fields__.values()}
        self.assertEqual(
            fields,
            {"provider_id", "directory", "base_url", "model", "enabled", "has_api_key"},
        )
        self.assertNotIn("api_key", fields)

    def test_live_userspace_discovers_zhipu(self) -> None:
        root = ProjectContext.path.get_assistant_providers_directory()
        if not (root / "zhipu" / "config.py").is_file():
            self.skipTest("userspace assistant providers 未安装")
        zhipu = Assistant.get_provider("zhipu")
        self.assertIsNotNone(zhipu)
        assert zhipu is not None
        self.assertEqual(zhipu.provider_id, "zhipu")
        self.assertEqual(zhipu.model, "glm-4-flash")
        self.assertTrue(zhipu.base_url.startswith("https://"))
        self.assertTrue(zhipu.directory.is_dir())
        ids = [item.provider_id for item in Assistant.list_providers()]
        self.assertIn("zhipu", ids)

    def test_live_chat_pong(self) -> None:
        if os.environ.get("NTQ_ASSISTANT_LIVE") != "1":
            self.skipTest("set NTQ_ASSISTANT_LIVE=1 to hit the real provider")
        zhipu = Assistant.get_provider("zhipu")
        if zhipu is None or not zhipu.has_api_key:
            self.skipTest("zhipu 未配置密钥")
        reply = Assistant.chat("只回复 pong", provider_id="zhipu")
        self.assertTrue(str(reply).strip())
        self.assertNotIn("Bearer", reply)


if __name__ == "__main__":
    unittest.main()
