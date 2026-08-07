"""post-upgrade 收尾动作执行器。"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from core.infra.update import Update
from core.infra.update.core.post_upgrade.registry import PostUpgradeRegistry

pytestmark = pytest.mark.force_run


def test_run_executes_registered_actions_in_order():
    PostUpgradeRegistry.clear()
    seen: list[str] = []

    @Update.post_upgrade.register("a_first")
    def _a(repo_root: Path, context: dict) -> None:
        seen.append("a")

    @Update.post_upgrade.register("b_second")
    def _b(repo_root: Path, context: dict) -> None:
        seen.append("b")

    with tempfile.TemporaryDirectory() as td:
        result = Update.post_upgrade.run(Path(td), context={"k": 1})

    assert result.skipped is False
    assert result.executed_count == 2
    assert result.action_ids == ["a_first", "b_second"]
    assert seen == ["a", "b"]

    PostUpgradeRegistry.clear()
