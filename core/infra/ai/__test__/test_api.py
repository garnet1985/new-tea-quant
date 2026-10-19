"""infra.ai AiChannel 契约测试。"""

from __future__ import annotations

import os
import unittest

import pytest

from core.infra.project_context import ProjectContext
from core.infra.ai import AiChannel
from core.infra.ai.contracts import AiError, ProviderInfo

pytestmark = pytest.mark.force_run


class TestAiChannelApi(unittest.TestCase):
    def test_facade_export(self) -> None:
        import core.infra.ai as pkg

        self.assertEqual(pkg.__all__, ["AiChannel"])
        self.assertFalse(hasattr(pkg, "ProviderInfo"))

    def test_list_and_get_callable(self) -> None:
        self.assertTrue(callable(AiChannel.list_providers))
        self.assertTrue(callable(AiChannel.get_provider))
        self.assertTrue(callable(AiChannel.set_api_key))
        self.assertTrue(callable(AiChannel.complete))
        self.assertIsNone(AiChannel.get_provider(""))
        self.assertIsNone(AiChannel.get_provider("../secret"))
        providers = AiChannel.list_providers()
        self.assertIsInstance(providers, list)

    def test_complete_rejects_blank_messages(self) -> None:
        with self.assertRaises(AiError) as ctx:
            AiChannel.complete([])
        self.assertIn("消息", str(ctx.exception))
        self.assertNotIn("Bearer", str(ctx.exception))

    def test_provider_info_fields(self) -> None:
        fields = {item.name for item in ProviderInfo.__dataclass_fields__.values()}
        self.assertEqual(
            fields,
            {"provider_id", "directory", "base_url", "model", "enabled", "has_api_key"},
        )
        self.assertNotIn("api_key", fields)

    def test_live_userspace_discovers_provider(self) -> None:
        root = ProjectContext.path.get_ai_providers_directory()
        if not (root / "zhipu" / "config.py").is_file():
            if not any(AiChannel.list_providers()):
                self.skipTest("userspace AI providers 未安装")
            return
        zhipu = AiChannel.get_provider("zhipu")
        self.assertIsNotNone(zhipu)
        assert zhipu is not None
        self.assertEqual(zhipu.provider_id, "zhipu")
        self.assertTrue(zhipu.base_url.startswith("https://"))

    def test_live_complete_pong(self) -> None:
        if os.environ.get("NTQ_AI_LIVE") != "1":
            self.skipTest("set NTQ_AI_LIVE=1 to hit the real provider")
        zhipu = AiChannel.get_provider("zhipu")
        if zhipu is None or not zhipu.has_api_key:
            self.skipTest("zhipu 未配置密钥")
        result = AiChannel.complete(
            [{"role": "user", "content": "只回复 pong"}],
            provider_id="zhipu",
        )
        self.assertTrue(result.reply.strip())
        self.assertNotIn("Bearer", result.reply)


if __name__ == "__main__":
    unittest.main()
