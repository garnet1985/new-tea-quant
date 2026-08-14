"""post-upgrade 收尾动作执行器。"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from core.infra.updater import Updater
from core.infra.updater.core.post_upgrade.registry import PostUpgradeRegistry

pytestmark = pytest.mark.force_run


def test_run_executes_registered_actions_in_order():
    PostUpgradeRegistry.clear()
    seen: list[str] = []

    @Updater.post_upgrade.register("a_first")
    def _a(repo_root: Path, context: dict) -> None:
        seen.append("a")

    @Updater.post_upgrade.register("b_second")
    def _b(repo_root: Path, context: dict) -> None:
        seen.append("b")

    with tempfile.TemporaryDirectory() as td:
        result = Updater.post_upgrade.run(Path(td), context={"k": 1})

    assert result.skipped is False
    assert result.action_ids[:2] == ["a_first", "b_second"]
    assert seen == ["a", "b"]
    assert "sync_userspace_updater" in result.action_ids

    PostUpgradeRegistry.clear()
