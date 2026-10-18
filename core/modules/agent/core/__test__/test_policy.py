"""写入准则：模型点名的路径不能逃出三个目录。"""

from __future__ import annotations

import unittest

import pytest

from core.infra.project_context import ProjectContext
from core.modules.agent.contracts import AgentError
from core.modules.agent.core.policy import resolve_user_write_path

pytestmark = pytest.mark.force_run


class TestWritePolicy(unittest.TestCase):
    def test_allows_strategy_tag_and_adapter_files(self) -> None:
        path = ProjectContext.path
        strategy = resolve_user_write_path("strategies/macd_cross/strategy.py")
        tag = resolve_user_write_path("extensions/tags/demo/tag.py")
        adapter = resolve_user_write_path("extensions/adapters/demo/adapter.py")

        self.assertTrue(strategy.is_relative_to(path.get_strategies_root().resolve()))
        self.assertTrue(tag.is_relative_to(path.get_tags_root().resolve()))
        self.assertTrue(adapter.is_relative_to(path.get_adapters_directory().resolve()))
        self.assertEqual(strategy.name, "strategy.py")

    def test_rejects_paths_outside_write_roots(self) -> None:
        rejected = (
            "",
            "   ",
            "/etc/passwd",
            "../core/system.json",
            "core/modules/agent/agent.py",
            "strategies",
            "extensions/assistant/providers/deepseek/api_key.txt",
            "system/membership/membership_token.txt",
            "strategies/../extensions/assistant/providers/deepseek/api_key.txt",
        )
        for relative in rejected:
            with self.subTest(relative=relative):
                with self.assertRaises(AgentError) as ctx:
                    resolve_user_write_path(relative)
                self.assertNotIn("Bearer", str(ctx.exception))
                self.assertNotIn("sk-", str(ctx.exception))
